"""
SaleEventAgent
==============

Triggered once per “Publish sale” action.  It:

1. Reads the current on‑sale ingredient IDs.
2. Calculates sale_ratio = (#ingredients on sale / total) for every meal
   using a single SQL JOIN + GROUP BY.
3. Picks the top‑N meals (default 10).
4. Extracts *pre‑computed* description_vectors from the DB and L2‑normalises
   them for cosine similarity search.
5. Returns a payload of meals + query vectors – user matching runs client‑side.

No chat history, no multi‑loop reasoning: single call → single response.
"""

from __future__ import annotations
import json
import numpy as np
from typing import List, Dict

from RecipeManager.Knowledge import models as db
from RecipeManager.Agent.VectorStore import UserSummaryVS


class SaleEventAgent:
    """One‑shot agent that, given current on‑sale items, returns:

        * Top‑N meals ranked by *sale‑ingredient ratio*
        * Normalised description vectors for client‑side user matching
        """
    def __init__(self, session, top_n: int = 10):
        self.session = session
        self.top_n = top_n

    # ---------------------------------------------------------------- helpers
    def _fetch_sale_ids(self) -> set[int]:
        return {
            row.ingredient_id
            for row in self.session.query(db.ShopItem.ingredient_id)
            .filter(db.ShopItem.on_sale.is_(True))
            .all()
        }

    def _rank_meals(self, sale_ids: set[int]) -> List[Dict]:
        if not sale_ids:
            return []

        # JOIN meals → meal_ingredient → shop_items (sale flag)
        q = (
            self.session.query(
                db.Meal.id,
                db.Meal.name,
                db.Meal.description_vector,
                db.MealIngredient.ingredient_id,
            )
            .join(db.MealIngredient, db.Meal.id == db.MealIngredient.meal_id)
        )

        stats: Dict[int, Dict] = {}
        for mid, name, vec_json, ing_id in q:
            rec = stats.setdefault(mid, {"name": name, "vec": vec_json, "sale": 0, "total": 0})
            rec["total"] += 1
            if ing_id in sale_ids:
                rec["sale"] += 1

        scored = [
            {
                "meal_id": mid,
                "name": rec["name"],
                "sale_ratio": rec["sale"] / rec["total"],
                "vec": rec["vec"],
            }
            for mid, rec in stats.items()
            if rec["sale"] > 0
        ]
        return sorted(scored, key=lambda x: -x["sale_ratio"])[: self.top_n]

    # ---------------------------------------------------------------- run
    def run(self) -> Dict:
        sale_ids = self._fetch_sale_ids()
        ranked = self._rank_meals(sale_ids)

        # normalise vectors for cosine similarity
        for row in ranked:
            vec = np.asarray(json.loads(row["vec"]), dtype="float32")
            vec /= np.linalg.norm(vec) + 1e-9
            row["vec"] = vec.tolist()

        # shape for Streamlit client
        return {
            "meals": [
                {"meal_id": r["meal_id"], "name": r["name"], "sale_ratio": r["sale_ratio"]}
                for r in ranked
            ],
            "user_query_vectors": {r["meal_id"]: r["vec"] for r in ranked},
        }


# simple CLI test
if __name__ == "__main__":
    from RecipeManager.Knowledge.models import get_session

    with get_session() as s:
        agent = SaleEventAgent(s, top_n=5)
        print(agent.run())
