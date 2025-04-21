"""
Manages user profiles, purchases, baskets, and conversation logs.
"""
from typing import List, Optional
from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, func
from sqlalchemy.orm import relationship
import time

from RecipeManager.Knowledge.models import Customer, Purchase, Ingredient, ShopItem, get_session

class CustomerSession:
    """
    Class to handle user operations: adding users, tracking baskets, purchases, and conversations.
    """

    def __init__(self, customer_name: str, session):
        self.basket: List[Ingredient] = []
        self.total_price = 0.0
        self.session = session

        exist = session.query(Customer).filter(Customer.full_name == customer_name).first()
        if exist:
            self.name = exist.full_name
        else:
            self.name = self.add_user(customer_name).full_name

    def add_user(self, name: str) -> Customer:
        """
        Add a new user to the database.

        :return: The User object created.
        """
        user = Customer(full_name=name, email=f"DUMMY", summary="No summary available yet.",
                        numberOfConversations=0)
        self.session.add(user)
        self.session.commit()
        return user

    def add_to_basket(self, ingredient: Ingredient) -> None:
        """
        Add an ingredient to the user's basket.
        """

        shop_listing = self.session.query(ShopItem).filter(ShopItem.ingredient_id == ingredient.id).first()
        if shop_listing:
            self.basket.append(ingredient)
            self.total_price += shop_listing.price

    def remove_from_basket(self, ingredient: Ingredient) -> None:
        if ingredient in self.basket:
            self.basket.remove(ingredient)
            self.total_price -= ingredient.shop_item.price

    def checkout(self) -> None:
        """
        Simulate checkout: move basket items to purchases and clear the basket.
        """
        checkout_time = time.time()
        customer = self.session.query(Customer).filter(Customer.full_name == self.name).first()
        for item in self.basket:
            quantity = 0
            while item in self.basket:
                quantity += 1
                self.basket.remove(item)
            shop_listing = self.session.query(ShopItem).filter(ShopItem.ingredient_id == item.id).first()
            purchase = Purchase(customer_id=customer.id,
                                ingredient_id=item.id,
                                price=shop_listing.price,
                                timestamp=checkout_time,
                                quantity=quantity)
            self.session.add(purchase)
        self.session.commit()
        self.basket = []
        self.total_price = 0.0

