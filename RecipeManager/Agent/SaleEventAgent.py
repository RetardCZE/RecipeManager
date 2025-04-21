"""
Agent that detects ingredient sales and notifies users with recipe recommendations.
"""
from typing import List, Optional
import random
# Assuming MealDatabase and UserManager are accessible for querying data
from RecipeManager.Knowledge.MealDatabase import Meal, Ingredient, MealIngredient, ShopItem
from RecipeManager.Knowledge.UserManager import UserManager


class SaleEventAgent:
    """
    Agent to detect sales events in the shop and notify users with relevant recipe recommendations.
    """

    def __init__(self, user_manager: UserManager):
        """
        Initialize the sale event agent with access to the user manager.

        :param user_manager: UserManager instance to manage user data and notifications.
        """
        self.user_manager = user_manager

    def detect_and_notify(self) -> None:
        """
        Detect ingredients that are on sale and send recipe recommendations to interested users.
        For each ingredient on sale, find recipes containing that ingredient and notify users
        who have previously purchased that ingredient (or all users if none have).
        """
        session = self.user_manager.db.session
        # Query all ingredients currently on sale
        sale_items: List[ShopItem] = session.query(ShopItem).filter(ShopItem.on_sale == True).all()
        for sale_item in sale_items:
            ingredient: Ingredient = sale_item.ingredient  # get the Ingredient object
            if ingredient is None:
                continue
            # Find all meals that include this ingredient
            meal_links: List[MealIngredient] = session.query(MealIngredient).filter(
                MealIngredient.ingredient_id == ingredient.id).all()
            if not meal_links:
                continue
            # Choose one meal to recommend (random choice for variety)
            meal_link = random.choice(meal_links)
            meal: Meal = meal_link.meal
            # Construct a recommendation message
            meal_name = meal.name
            ingredient_name = ingredient.name
            # Optionally include a short part of meal description if available
            if meal.description:
                # Use just the first sentence or brief snippet of description
                snippet = meal.description.split('.')[0]
                message = (f"Good news! {ingredient_name} is on sale. "
                           f"You could use it to make \"{meal_name}\" - {snippet.strip()}...")
            else:
                message = (f"Good news! {ingredient_name} is on sale. "
                           f"How about trying the recipe \"{meal_name}\" which uses it?")
            # Determine which users to notify
            interested_users = set()
            # Users who purchased this ingredient before
            purchases = [p for p in ingredient.purchases] if hasattr(ingredient, 'purchases') else []
            for purchase in purchases:
                interested_users.add(purchase.user_id)
            # If no specific users, notify all users as a general recommendation
            if not interested_users:
                all_user_ids = [user.id for user in session.query(self.user_manager.User).all()]
                interested_users = set(all_user_ids)
            # Send notification to each interested user
            for user_id in interested_users:
                # Log the notification via UserManager (e.g., add to conversation history)
                self.user_manager.add_conversation_entry(user_id=user_id, text=message, role="assistant")
                # In a real system, this could send an email or app notification.
                # Here we simply log to console for demonstration.
                print(f"[Notification] User {user_id}: {message}")
