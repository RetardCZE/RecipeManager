"""
Handles database interactions with Meals, Ingredients, Shop, and Users.
"""
from typing import List, Tuple, Optional
from sqlalchemy import create_engine, text, Column, Integer, String, ForeignKey, Float, Boolean, Table, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from pathlib import Path

Base = declarative_base()
db_path = Path(__file__).parent / "meal_db.db"
path = f"sqlite:///{str(db_path)}"
engine = create_engine(path)


class MealIngredient(Base):
    __tablename__ = 'meal_ingredient'
    meal_id       = Column(Integer, ForeignKey('meals.id'), primary_key=True)
    pair_id       = Column(Integer, primary_key=True)                 # NEW
    ingredient_id = Column(Integer, ForeignKey('ingredients.id'))
    measure       = Column(String, default="")

    meal        = relationship("Meal",       back_populates="ingredients")
    ingredient  = relationship("Ingredient", back_populates="meals")


class Meal(Base):
    __tablename__ = 'meals'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=True)
    area = Column(String, nullable=True)
    instructions = Column(Text, nullable=True)
    instructions_vector = Column(String, nullable=True)
    description = Column(Text, nullable=True)  # LLM-generated description
    description_vector = Column(String, nullable=True)
    ingredients = relationship("MealIngredient", back_populates="meal")


class Ingredient(Base):
    __tablename__ = 'ingredients'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    description_vector = Column(String, nullable=True)
    type = Column(String, nullable=True)

    meals = relationship("MealIngredient", back_populates="ingredient")

    shop_item = relationship("ShopItem", uselist=False, back_populates="ingredient")
    purchases = relationship("Purchase", back_populates="ingredient")

class ShopItem(Base):
    __tablename__ = 'shop_items'
    id = Column(Integer, primary_key=True, autoincrement=True)
    ingredient_id = Column(Integer, ForeignKey('ingredients.id'), unique=True)
    price = Column(Float, nullable=False)
    on_sale = Column(Boolean, default=False)
    discount = Column(Float, nullable=True)

    ingredient = relationship("Ingredient", back_populates="shop_item")

class Purchase(Base):
    __tablename__ = 'purchases'
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey('customers.id'))
    ingredient_id = Column(Integer, ForeignKey('ingredients.id'))
    timestamp = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)

    user = relationship("Customer", back_populates="purchases")
    ingredient = relationship("Ingredient", back_populates="purchases")

class Customer(Base):
    __tablename__ = 'customers'
    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False)

    summary = Column(Text, nullable=False)
    summary_vector = Column(String, nullable=False)
    numberOfConversations = Column(Integer, nullable=False)

    purchases = relationship("Purchase", back_populates="user")


Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def get_session() -> Session:
    """Return a **new** SQLAlchemy session bound to the project’s SQLite database.
    """
    return Session()