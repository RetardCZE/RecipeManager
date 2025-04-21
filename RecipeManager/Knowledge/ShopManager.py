"""
Populates the shop with a subset of ingredients and assigns prices and sale flags.
"""
import random
from typing import List
from RecipeManager.Knowledge.models import Ingredient, ShopItem, Purchase, get_session


class ShopManager:
    """
    Handles populating and managing the shop inventory.
    """
    def __init__(self, session):
        self.session = session

    def populate_shop(self, sale_fraction: float = 0.2, price_range: tuple = (1.0, 10.0)) -> None:
        """
        Populate 80% of ingredients to the shop with random prices and set some on sale.

        :param sale_fraction: Fraction of ingredients to put on sale (0.2 means 20% on sale).
        :param price_range: Tuple indicating the min and max price range for ingredients.
        """
        with get_session() as session:
            ingredients: List[Ingredient] = session.query(Ingredient).all()
            num_on_sale = int(len(ingredients) * sale_fraction)
            sale_indices = set(random.sample(range(len(ingredients)), num_on_sale))
            for idx, ingredient in enumerate(ingredients):
                exists = session.query(ShopItem).filter(ShopItem.ingredient_id == ingredient.id).first()
                if not exists:
                    price = round(random.uniform(*price_range), 2)
                    on_sale = False
                    if idx in sale_indices:
                        # on sale with a discount
                        discount = round(1 - random.uniform(0.15, 0.5), 2)
                        on_sale = True
                        new_shop_item = ShopItem(ingredient_id=ingredient.id, price=price, on_sale=on_sale, discount=discount)
                        print(f"Adding ingredient {ingredient.name} to the shop with discount {discount} and price {price}...")
                    else:
                        new_shop_item = ShopItem(ingredient_id=ingredient.id, price=price, on_sale=on_sale)
                        print(
                            f"Adding ingredient {ingredient.name} to the shop with price {price}...")
                    session.add(new_shop_item)
                    session.commit()

if __name__ == "__main__":
    manager = ShopManager()
    manager.populate_shop()