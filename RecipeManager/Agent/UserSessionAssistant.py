"""
UserSessionAssistant
====================

Chat agent that suggests meals, builds a basket, and manages token‑efficient
memory by condensing old turns into a single summary paragraph.
"""

from __future__ import annotations
import json, textwrap
from typing import Any, Dict, List, Optional

from RecipeManager.Agent.OpenAIConnector import OpenAIClient
from RecipeManager.Knowledge.UserManager import CustomerSession
from RecipeManager.Knowledge.ShopManager import ShopManager
from RecipeManager.Knowledge import models as db
from RecipeManager.Agent.VectorStore import (
    IngredientDescriptionVS, MealDescriptionVS, MealInstructionsVS
)
import time

from openai.types.chat import ChatCompletionMessageParam, ChatCompletionMessageToolCallParam
from RecipeManager.Agent import TOOL_SCHEMAS

class UserSessionAgent(OpenAIClient):
    """Conversational agent assisting a shopper with meals and basket building.

        * Maintains a running **LLM memory** summarised after 15 turns.
        * Exposes OpenAI tool‑calling functions for vector search, price lookup,
          basket ops, etc.
        * Refreshes the system prompt’s basket line after every mutation.
        * `checkout()` persists purchases and regenerates an embedding‑ready user
          summary.  See inline docstrings for each tool.
        """
    def __init__(self, api_key: str, user_name: str, session):
        super().__init__(api_key)
        self.session = session

        # helpers
        self.customer_session = CustomerSession(user_name, session)
        self.shop_manager = ShopManager(session)

        # vector stores
        self.vs_ing  = IngredientDescriptionVS(session, self)
        self.vs_meal = MealDescriptionVS(session, self)
        self.vs_ins  = MealInstructionsVS(session, self)

        # chat state
        self.history: List[ChatCompletionMessageParam] = []
        self.max_loops = 5
        self._init_system_prompt()

    # ────────────────── system prompt & basket line ─────────────────
    TEMPLATE = textwrap.dedent("""\
        You are RecipeManager, a friendly culinary assistant.
        Goal → help the user choose meals they’ll enjoy and build a shopping basket.
        {customer_summary}
        {basket_synopsis}
        Do not force hard meal rules to user. Listen to his needs and use his summary subtle in background.
        Use the provided tools strictly when you need factual data (search, price lookup, basket ops).
        After any basket change, confirm and show the new basket state.
        On checkout, provide cooking tips and a compact session summary.
    """)

    def _init_system_prompt(self):
        cust = (
            self.session.query(db.Customer)
            .filter(db.Customer.full_name == self.customer_session.name).first()
        )
        summary_line = (
            f"User summary: {cust.summary}" if cust and cust.summary else "User summary: (none yet)"
        )
        self.system_msg: ChatCompletionMessageParam = {
            "role": "system",
            "content": self.TEMPLATE.format(customer_summary=summary_line,
                                            basket_synopsis="Basket: (empty)")
        }
        # dedicated summary placeholder comes immediately after system
        self.summary_msg: ChatCompletionMessageParam = {
            "role": "assistant",
            "content": "(conversation summary will appear here as needed)"
        }

    def _basket_synopsis(self) -> str:
        items: dict[str, int] = {}
        for ing in self.customer_session.basket:
            items[ing.name] = items.get(ing.name, 0) + 1
        if not items:
            return "Basket: (empty)"
        detail = ", ".join(f"{q}× {n}" for n, q in items.items())
        return f"Basket: {detail} – total €{self.customer_session.total_price:0.2f}"

    def _refresh_basket_line(self):
        self.system_msg["content"] = self.system_msg["content"].rsplit("Basket:", 1)[0] + self._basket_synopsis()

    # ──────────────────────── chat I/O helpers ──────────────────────
    def add_user_message(self, content: str):
        self.history.append({"role": "user", "content": content})
        self.evaluate()

    def add_assistant_message(self, msg: Dict[str, Any]):
        self.history.append({"role": "assistant", **msg})
        for tc in msg.get("tool_calls", []):
            self._handle_tool_call(tc)

    def _handle_tool_call(self, tc: dict):
        name = tc["function"]["name"]
        args_json = tc["function"]["arguments"]
        args = json.loads(args_json) if isinstance(args_json, str) else args_json
        func = getattr(self, name, None)
        print(f"Tool call: {name}({args})")
        try:
            result = func(**args) if callable(func) else f"Unknown tool '{name}'"
        except Exception as exc:
            result = f"Error from {name}: {exc}"
        print(result)
        self.history.append(
            {"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(result, ensure_ascii=False)}
        )

    # ───────────────────────── condense logic ───────────────────────
    HARD_CAP = 26          # system + summary + 24 turns
    TRIGGER  = 15          # after which we summarise older msgs

    def _condense_history(self):
        """Summarise oldest turns into summary_msg to stay under HARD_CAP."""
        if len(self.history) <= self.HARD_CAP:
            return

        # slice off messages that need summarising
        overflow = self.history[:-self.TRIGGER]
        self.history = self.history[-self.TRIGGER:]

        # build text chunk
        text = "\n".join(f"{m['role']}: {m['content']}" for m in overflow if m["role"] in {"user","assistant"})
        prompt = [
            {"role": "system", "content":
             "Summarise the following chat history in <150 words, preserve facts:"},
            {"role": "user", "content": text}
        ]
        summary = self.get_chat_completion(prompt, max_tokens=200).content
        # fold into running summary
        prev = self.summary_msg["content"] if "(conversation summary" not in self.summary_msg["content"] else ""
        self.summary_msg["content"] = f"{prev}\n{summary}".strip()

    # ───────────────────────── main evaluate ────────────────────────
    def evaluate(self):
        loops = 0
        while True:
            self._condense_history()
            msgs = [self.system_msg, self.summary_msg] + self.history

            # include tool JSON + allow model to decide
            if loops >= self.max_loops:
                msgs += {'role': 'system', 'content': 'You cant use any more tools. Finish answering.'}
                assistant = self.get_chat_completion(
                    messages=msgs,
                )
            else:
                assistant = self.get_chat_completion(
                    messages=msgs,
                    tools=TOOL_SCHEMAS,
                    tool_choice="auto",
                )
            parsed = {"content": assistant.content}
            # OpenAI SDK attaches a list of tool_calls, if any
            if getattr(assistant, "tool_calls", None):
                parsed["tool_calls"] = [tc.model_dump() for tc in assistant.tool_calls]
            self.add_assistant_message(parsed)
            last = self.history[-1]
            if last["role"] == "assistant" and "tool_calls" not in last:
                break
            loops += 1

    # ---------------------------------------------------------------- tools --
    # Each method below can be exposed via OpenAI tool schema

    # ---- retrieval
    def retrieve_ingredient(self, description: str, k: int = 5):
        results = self.vs_ing.retrieve(description, k)
        ing_objs = (
            self.session.query(db.Ingredient)
            .filter(db.Ingredient.id.in_([r.id for r in results]))
            .all()
        )
        return [{"id": ing.id, "name": ing.name} for ing in ing_objs]

    def retrieve_meal(self, description: str, k: int = 5):
        results = self.vs_meal.retrieve(description, k)
        meals = self.session.query(db.Meal).filter(db.Meal.id.in_([r.id for r in results])).all()
        return [{"id": m.id, "name": m.name} for m in meals]

    def retrieve_meal_by_instructions(self, instructions: str, k: int = 5):
        results = self.vs_ins.retrieve(instructions, k)
        meals = self.session.query(db.Meal).filter(db.Meal.id.in_([r.id for r in results])).all()
        return [{"id": m.id, "name": m.name} for m in meals]

    # ---- shop / basket
    def list_ingredients(self):
        return [
            {"id": ing.id, "name": ing.name}
            for ing in self.session.query(db.Ingredient).all()
        ]

    def get_price(self, ingredient_id: int):
        item = (
            self.session.query(db.ShopItem)
            .filter(db.ShopItem.ingredient_id == ingredient_id)
            .first()
        )
        if not item:
            raise ValueError("ingredient not in shop")
        return {
            "price": item.price,
            "on_sale": item.on_sale,
            "discount": item.discount,
        }

    def add_to_basket(self, ingredient_id: int, qty: int = 1):
        ing = self.session.get(db.Ingredient, ingredient_id)
        if not ing:
            raise ValueError("ingredient not found")
        for _ in range(max(1, qty)):
            self.customer_session.add_to_basket(ing)
        self._refresh_basket_line()
        return {"items": [i.name for i in self.customer_session.basket],
                "total": self.customer_session.total_price}

    def list_sale_items(self):
        rows = (
            self.session.query(db.ShopItem, db.Ingredient)
            .join(db.Ingredient, db.ShopItem.ingredient_id == db.Ingredient.id)
            .filter(db.ShopItem.on_sale.is_(True))
            .all()
        )
        return [
            {
                "ingredient_id": si.ingredient_id,
                "name": ing.name,
                "price": si.price,
                "discount": si.discount,
            }
            for si, ing in rows
        ]

    def retrieve_meals_with_sale_overlap(self, min_overlap: int = 1, k: int = 10):
        sale_ids = {
            row.ingredient_id
            for row in self.session.query(db.ShopItem.ingredient_id)
            .filter(db.ShopItem.on_sale.is_(True))
        }
        if not sale_ids:
            return []

        q = (
            self.session.query(
                db.Meal.id, db.Meal.name, db.Meal.description, db.MealIngredient.ingredient_id
            )
            .join(db.MealIngredient, db.Meal.id == db.MealIngredient.meal_id)
            .filter(db.MealIngredient.ingredient_id.in_(sale_ids))
        )
        counts, names, descs = {}, {}, {}
        for mid, n, d, _ in q.all():
            counts[mid] = counts.get(mid, 0) + 1
            names[mid], descs[mid] = n, d

        meals = sorted(
            [(mid, ov) for mid, ov in counts.items() if ov >= max(1, min_overlap)],
            key=lambda x: -x[1],
        )[:k]

        return [
            {
                "meal_id": mid,
                "name": names[mid],
                "overlap": ov,
                "description": descs[mid],
            }
            for mid, ov in meals
        ]

    # ───────── SQL detail helpers ─────────────────────────────────────
    def get_meal_details(self, meal_id: int):
        m = self.session.get(db.Meal, meal_id)
        if not m:
            raise ValueError("meal not found")
        return {
            "id": m.id,
            "name": m.name,
            "category": m.category,
            "area": m.area,
            "description": m.description,
            "instructions": m.instructions,
        }

    def get_meal_ingredients(self, meal_id: int):
        rows = (
            self.session.query(
                db.Ingredient.id,
                db.Ingredient.name,
                db.MealIngredient.measure,
                db.ShopItem.price,
                db.ShopItem.on_sale,
                db.ShopItem.discount,
            )
            .join(db.MealIngredient, db.Ingredient.id == db.MealIngredient.ingredient_id)
            .outerjoin(db.ShopItem, db.ShopItem.ingredient_id == db.Ingredient.id)
            .filter(db.MealIngredient.meal_id == meal_id)
            .all()
        )
        return [
            {
                "ingredient_id": iid,
                "name": name,
                "measure": meas,
                "price": price,
                "on_sale": on_sale,
                "discount": disc,
            }
            for iid, name, meas, price, on_sale, disc in rows
        ]

    def get_ingredient_details(self, ingredient_id: int):
        i = self.session.get(db.Ingredient, ingredient_id)
        if not i:
            raise ValueError("ingredient not found")
        return {
            "id": i.id,
            "name": i.name,
            "description": i.description,
            "type": i.type,
        }

    def add_meal_to_basket(self, meal_id: int, servings: int = 1):
        base = self.get_meal_ingredients(meal_id)
        if not base:
            raise ValueError("meal has no shop‑listed ingredients")
        for item in base:
            ing = self.session.get(db.Ingredient, item["ingredient_id"])
            for _ in range(max(1, servings)):
                self.customer_session.add_to_basket(ing)
        self._refresh_basket_line()
        return {
            "items": [i.name for i in self.customer_session.basket],
            "total": self.customer_session.total_price,
        }

    # ------------------------------------------------------------------ checkout
    def checkout(self):
        """
        Persist basket → purchases, regenerate & embed user summary,
        then clear basket. Returns dict for UI.
        """
        if not self.customer_session.basket:
            raise ValueError("basket empty")

        cust = (
            self.session.query(db.Customer)
            .filter(db.Customer.full_name == self.customer_session.name)
            .first()
        )
        if not cust:
            raise RuntimeError("customer not found")

        ts = time.time()
        rows = []
        for ing in list(self.customer_session.basket):  # copy; will be cleared
            shop = (
                self.session.query(db.ShopItem)
                .filter(db.ShopItem.ingredient_id == ing.id)
                .first()
            )
            purch = db.Purchase(
                customer_id=cust.id,
                ingredient_id=ing.id,
                timestamp=ts,
                price=shop.price,
                quantity=1,
            )
            self.session.add(purch)
            rows.append({"name": ing.name, "€": shop.price})
        self.session.commit()

        # -------- regenerate summary (old + trend) ----------------------
        SUMM_PROMPT = [
            {"role": "system", "content":
                "You are updating a short user profile (<80 words). "
                "Merge the OLD summary with what the user talked about lately. "
                "Highlight recent cooking trends or diet changes."},
            {"role": "user", "content": f"OLD:\n{cust.summary}\n\n"
                                        f"RECENT CHAT:\n"
                                        + "\n".join(
                f'{m["role"]}: {m["content"]}'
                for m in self.history[-15:]
                if m["role"] in {"user", "assistant"}
            )}
        ]
        new_summary = self.get_chat_completion(SUMM_PROMPT, max_tokens=120).content
        cust.summary = new_summary
        cust.summary_vector = json.dumps(self.get_embedding(new_summary))
        cust.numberOfConversations += 1
        self.session.commit()

        # -------- reset basket & internal state ------------------------
        self.customer_session.basket.clear()
        self.customer_session.total_price = 0.0
        self._refresh_basket_line()

        return {
            "purchases": rows,
            "new_summary": new_summary,
        }
