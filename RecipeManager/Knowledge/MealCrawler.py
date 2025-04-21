"""
MealCrawler
===========

Fetches the complete public recipe corpus from TheMealDB (https://www.themealdb.com/api.php).

The crawler is intentionally *read‑only*: it only returns raw meal dictionaries so that
higher‑level loaders (e.g., PopulateAll.py) can decide how to transform / persist them.

Usage
-----
crawler = MealCrawler()
all_meals = crawler.fetch_all_meals()          # List[dict] – each dict is the raw JSON block
"""

from string import ascii_lowercase
from typing import List, Dict, Any
import logging
import time

from RecipeManager.Knowledge.MealDBConnector import TheMealDBClient
from RecipeManager.Knowledge.models import Meal, Ingredient, MealIngredient, get_session
from RecipeManager.Agent.OpenAIConnector import OpenAIClient

class MealCrawler:
    """Crawl the public MealDB for *all* recipes (26 × A‑Z pass).

    The crawler is **idempotent**: it returns raw payloads; DB persistence and
    embedding are left to higher‑level loaders so tests can mock the HTTP layer
    independently.  Optionally throttles requests (default 0.25 s)."""

    def __init__(self, throttle: float | None = 0.25) -> None:
        """
        Parameters
        ----------
        throttle : float | None, default 0.25
            Optional sleep (seconds) between API calls to avoid hammering the free endpoint.
            Set to None or 0 to disable.
        """
        self.client = TheMealDBClient()
        self.throttle = throttle

    def fetch_all_meals(self) -> List[Dict[str, Any]]:
        """Return a list of **unique** recipe dictionaries from MealDB."""
        seen_ids: set[int] = set()
        all_meals: List[Dict[str, Any]] = []

        for letter in ascii_lowercase:
            try:
                payload = self.client.search_meal_by_first_letter(letter)
            except Exception as exc:
                logging.warning("API error on letter '%s': %s", letter, exc)
                continue

            meals_for_letter = payload.get("meals") if payload else None
            if not meals_for_letter:
                if self.throttle:
                    time.sleep(self.throttle)
                continue

            for meal in meals_for_letter:
                try:
                    meal_id = int(meal["idMeal"])
                except (KeyError, ValueError):
                    continue
                if meal_id in seen_ids:
                    continue
                seen_ids.add(meal_id)
                all_meals.append(meal)

            if self.throttle:
                time.sleep(self.throttle)

        logging.info("Fetched %d unique meals from MealDB", len(all_meals))
        return all_meals

    def fetch_all_ingredients(self):
        return TheMealDBClient().list_all_ingredients()['meals']


def enrich_ingredient_via_llm(client: OpenAIClient, ingredient_name: str) -> Dict[str, str]:
    """Ask the LLM for a JSON description of *ingredient_name* (3 keys only).

    Falls back to empty strings if the LLM fails.  The JSON schema is enforced
    via the function‑calling API.
    """
    system_msg = {
        "role": "system",
        "content": (
            "You are a culinary expert. "
            "When I give you an ingredient name, respond ONLY with a JSON object "
            "containing exactly these keys:\n"
            '  "name"         — canonical English name of the ingredient\n'
            '  "description"  — one concise sentence describing it (max 25 words)\n'
            '  "type"         — broad category, e.g. "spice", "meat", "vegetable", "dairy"\n\n'
            "Do not include markdown, comments, or additional keys."
        ),
    }
    user_msg = {
        "role": "user",
        "content": ingredient_name,
    }
    rformat = {
            "format": {
                "type": "json_schema",
                "name": "calendar_event",
                "schema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "The name of the ingredient.",
                        },
                        "description": {
                            "type": "string",
                            "description": "Description of the ingredient. Should contain usual usage and alternatives, health benefits or cons etc... Pure text with around 50-100 words.",
                        },
                        "type": {
                            "type": "string",
                            "description": "Type of the ingredient eg.: Fish, meat, spice, vegetable, dairy, etc.",
                        },
                    },
                    "required": ["name", "description", "type"],
                    "additionalProperties": False
                },
                "strict": True
            }
        }
    response = client.get_chat_completion_json([system_msg, user_msg], rformat=rformat)
    try:
        return json.loads(response.output[0].content[0].text)
    except Exception as exc:  # pragma: no cover
        logging.error("LLM failed to enrich ingredient '%s': %s", ingredient_name, exc)
        # Fallback with minimal data so the pipeline can continue.
        return {"name": ingredient_name, "description": "", "type": ""}

if __name__ == "__main__":
    import os
    import json
    from RecipeManager.Agent.OpenAIConnector import OpenAIClient
    crawler = MealCrawler(throttle=0.1)
    meals = crawler.fetch_all_meals()
    ingredients = crawler.fetch_all_ingredients()
    client = OpenAIClient(api_key=os.environ["OPENAI_API_KEY"])

    # first save all ingredients
    with get_session() as session:
        for idx, ingredient in enumerate(ingredients):
            print(f'{idx}/{len(ingredients)} ingredient: {ingredient["strIngredient"]}')
            exists = session.query(Ingredient).filter(Ingredient.name == ingredient['strIngredient']).first()
            if not exists:
                new_ingredient = Ingredient(name=ingredient['strIngredient'],
                                            description=ingredient['strDescription'],
                                            type=ingredient['strType'])
                session.add(new_ingredient)
            else:
                new_ingredient = exists
            if new_ingredient.description_vector is None and new_ingredient.description:
                vectors = client.get_embeddings([new_ingredient.description], model="text-embedding-3-small")
                new_ingredient.description_vector = json.dumps(vectors[0])

        session.commit()

    client = OpenAIClient(api_key=os.environ["OPENAI_API_KEY"])
    system_message = {"content": ("You are a culinary expert. When given a recipe, create a short description of the meal."
                      "The goal is to summarize all the important stuff about the meal. Like its type, for what diets it suitable,"
                      " if its healthy or not, etc. The description shouldn't be longer than one paragraph"),
                      "role": "system"}
    with (get_session() as session):
        for idx, meal in enumerate(meals):
            print(f'{idx}/{len(meals)} meal: {meal["strMeal"]}')
            exists = session.query(Meal).filter(Meal.name == meal['strMeal']).first()
            # this first part is for uploading the meals without relation to the ingredients
            ingredient_dict = {meal[f'strIngredient{i}']: meal[f'strMeasure{i}']
                               for i in range(1, 21) if meal[f'strIngredient{i}']}
            if not exists:

                meal_message = {"role": "user",
                                "content": f"""
Meal: {meal['strMeal']}
Meal Type: {meal['strCategory']}
Meal Area: {meal['strArea']}
ingredients: {json.dumps(ingredient_dict, indent=4)}
Cook instructions: {meal['strInstructions']}
    """}

                llm_description = client.get_chat_completion([system_message, meal_message])

                new_meal = Meal(name=meal['strMeal'],
                                category=meal['strCategory'],
                                area=meal['strArea'],
                                instructions=meal['strInstructions'],
                                description=llm_description.content,
                                )
                session.add(new_meal)
                session.commit()
            else:
                new_meal = exists

            if new_meal.description_vector is None and new_meal.description:
                vectors = client.get_embeddings([new_meal.description], model="text-embedding-3-small")
                new_meal.description_vector = json.dumps(vectors[0])

            if new_meal.instructions_vector is None and new_meal.instructions:
                vectors = client.get_embeddings([new_meal.instructions], model="text-embedding-3-small")
                new_meal.instructions_vector = json.dumps(vectors[0])

            session.commit()
            # at this point we need to add the ingredients to the meal and check their existance in the database
            # here i need 2nd system message to fill description and type for missing ingredients

            for pair_id, (ingredient, measure) in enumerate(ingredient_dict.items()):
                exists = session.query(Ingredient).filter(Ingredient.name == ingredient).first()
                if not exists or not exists.description or not exists.type:
                    enriched = enrich_ingredient_via_llm(client, ingredient)
                    if not exists:
                        ingredient_obj = Ingredient(name=ingredient,
                                                    description=enriched["description"],
                                                    type=enriched["type"])
                        session.add(ingredient_obj)
                    else:
                        ingredient_obj = exists
                        ingredient_obj.description = enriched["description"]
                        ingredient_obj.type = enriched["type"]

                    # here we can place multiple similar ingredients, but right now I wont dealt with that
                    print(f"Enriched ingredient {ingredient} with description {enriched['description']}")
                    print("-------")
                else:
                    ingredient_obj = exists

                if ingredient_obj.description_vector is None and ingredient_obj.description:
                    vectors = client.get_embeddings([ingredient_obj.description], model="text-embedding-3-small")
                    ingredient_obj.description_vector = json.dumps(vectors[0])

                session.commit()
                is_connected = session.query(MealIngredient).filter(MealIngredient.meal_id == new_meal.id, MealIngredient.ingredient_id == ingredient_obj.id).first()
                if not is_connected:
                    new_meal_ingredient = MealIngredient(meal_id=new_meal.id, ingredient_id=exists.id,
                                                         pair_id=pair_id, measure=measure)
                    session.add(new_meal_ingredient)
                    print(f"Added ingredient {ingredient} to meal {meal['strMeal']} with measure {measure}")
                session.commit()



