from RecipeManager.Knowledge.models import get_session
from RecipeManager.Agent.UserSessionAssistant import UserSessionAgent
import os

"""
Populate the DB with three dummy customers for testing.

Run:
    python scripts/add_dummy_customers.py
"""

from RecipeManager.Knowledge.models import get_session, Customer
from RecipeManager.Agent.OpenAIConnector import OpenAIClient
import os, json

# ── 1. example data ────────────────────────────────────────────────────────────
# DUMMIES = [
#     {
#         "full_name": "Alice Baker",
#         "email": "alice@example.com",
#         "summary": (
#             "Enjoys quick vegetarian meals, avoids dairy, loves Mediterranean flavors. "
#             "Usually cooks twice a week and is price‑conscious."
#         ),
#         "convos": 7,
#     },
#     {
#         "full_name": "Bruno Carver",
#         "email": "bruno@example.com",
#         "summary": (
#             "Fitness‑oriented omnivore who tracks macros. Prefers high‑protein dishes, "
#             "minimal sugar, and experiments with new spice blends."
#         ),
#         "convos": 3,
#     },
#     {
#         "full_name": "Chloe Diaz",
#         "email": "chloe@example.com",
#         "summary": (
#             "Family cook for four (two kids). Favors budget‑friendly one‑pot recipes, "
#             "but enjoys baking on weekends. Allergic to peanuts."
#         ),
#         "convos": 12,
#     },
# ]



with get_session() as s:
    agent = UserSessionAgent(
        api_key=os.environ["OPENAI_API_KEY"],
        user_name="Alice Baker",
        session=s,
    )
    agent.add_user_message("I'd love something vegetarian for dinner.")
    print(agent.history)