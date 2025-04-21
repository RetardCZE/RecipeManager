"""
Add 20 diverse dummy customers with varied food profiles.
Run:
    python scripts/add_dummy_customers_20diverse.py
"""

from RecipeManager.Knowledge.models import get_session, Customer
from RecipeManager.Agent.OpenAIConnector import OpenAIClient
import os, json, random, time

# ── helper to embed summaries ────────────────────────────────────────────────
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAIClient(api_key) if api_key else None

def embed(text: str) -> str:
    if client:
        return json.dumps(client.get_embedding(text))
    # fallback 384‑dim zero vector
    return json.dumps([0.0] * 384)

# ── profiles -----------------------------------------------------------------
PROFILES = [
    {
        "full_name": "Liam Baker",
        "summary": (
            "Active college student; pescatarian diet for Omega‑3 intake but avoids "
            "red meat. Loves quick sheet‑pan dinners and seafood curries."
        ),
    },
    {
        "full_name": "Olivia Carver",
        "summary": (
            "Vegetarian marathon runner focused on iron‑rich legumes and whole‑grain "
            "bowls. Prefers Mediterranean spices and meal‑preps on Sundays."
        ),
    },
    {
        "full_name": "Noah Diaz",
        "summary": (
            "Family cook for three toddlers. Values slow‑cooker one‑pot meals that "
            "hide extra veggies. Budget‑conscious and seeks make‑ahead freezer dishes."
        ),
    },
    {
        "full_name": "Emma Ellis",
        "summary": (
            "Tech worker with peanut allergy; explores dairy‑free smoothie bowls and "
            "Asian noodle soups. Enjoys experimenting with tofu and miso."
        ),
    },
    {
        "full_name": "Oliver Foster",
        "summary": (
            "Weekend grill master. Omnivore who experiments with smoked meats and "
            "plant‑based burger alternatives. Tracks macros for strength training."
        ),
    },
    {
        "full_name": "Charlotte Garcia",
        "summary": (
            "High‑school teacher following a flexitarian plan — mostly plant‑based, "
            "but includes fish twice a week. Loves sheet‑pan roasted veggies."
        ),
    },
    {
        "full_name": "Elijah Hughes",
        "summary": (
            "Newly diagnosed celiac; strictly gluten‑free. Seeks hearty stews with "
            "rice or quinoa and naturally GF global cuisines like Mexican."
        ),
    },
    {
        "full_name": "Amelia Iverson",
        "summary": (
            "Budget student who batch‑cooks lentil dishes and chickpea curries. "
            "Uses a slow cooker for set‑and‑forget weeknight meals."
        ),
    },
    {
        "full_name": "James Jones",
        "summary": (
            "Keto‑leaning software engineer. Prefers high‑protein, low‑carb recipes "
            "with avocado, salmon, and cruciferous veggies; avoids sugar."
        ),
    },
    {
        "full_name": "Sophia Klein",
        "summary": (
            "New mom monitoring dairy sensitivity; experiments with oat‑milk baking "
            "and vitamin‑rich green smoothies."
        ),
    },
    # -------- second batch of 10 ------------------------------------------------
    {
        "full_name": "Matthew Lopez",
        "summary": (
            "Pescatarian who loves Mediterranean grain bowls and sustainable "
            "seafood. Uses air‑fryer for quick lunches."
        ),
    },
    {
        "full_name": "Isabella Morris",
        "summary": (
            "Vegan yoga instructor interested in high‑protein plant sources such "
            "as tempeh, seitan, and black‑bean pastas."
        ),
    },
    {
        "full_name": "Jacob Nguyen",
        "summary": (
            "Soups‑and‑stews enthusiast; keeps a rotating menu of crock‑pot "
            "comfort foods. Prefers mild spices and seasonal produce."
        ),
    },
    {
        "full_name": "Mia Owens",
        "summary": (
            "Adventurous foodie exploring global street food‑inspired dishes at home "
            "— likes Thai curries, Moroccan tagines, and Korean bibimbap."
        ),
    },
    {
        "full_name": "Michael Patel",
        "summary": (
            "Diabetic grandparent seeking low‑glycemic dinners and smart carb swaps "
            "such as cauliflower rice and zucchini noodles."
        ),
    },
    {
        "full_name": "Evelyn Quinn",
        "summary": (
            "Eco‑conscious flexitarian who gardens herbs and enjoys zero‑waste "
            "cooking challenges and pickling."
        ),
    },
    {
        "full_name": "Benjamin Reyes",
        "summary": (
            "Weight‑lifting pharmacist on a high‑protein meal plan; meal‑preps "
            "grilled chicken, quinoa, and steamed broccoli in bulk."
        ),
    },
    {
        "full_name": "Ava Singh",
        "summary": (
            "College vegan who craves spicy Indian‑fusion recipes and loves "
            "experiments with jackfruit tacos."
        ),
    },
    {
        "full_name": "Lucas Turner",
        "summary": (
            "Outdoor enthusiast relying on portable meals: trail‑mix bars, "
            "dehydrated soups, and foil‑packet campfire dinners."
        ),
    },
    {
        "full_name": "Harper Vargas",
        "summary": (
            "Allergy‑aware parent (milk & egg) cooks plant‑based breakfasts and "
            "nut‑free school lunches. Fan of overnight oats."
        ),
    },
]

# add random email & convo count
for p in PROFILES:
    p["email"] = f"{p['full_name'].replace(' ','.').lower()}@example.com"
    p["convos"] = random.randint(1, 15)

# ── insert -------------------------------------------------------------------
with get_session() as session:
    for p in PROFILES:
        if session.query(Customer).filter(Customer.full_name == p["full_name"]).first():
            print(f"{p['full_name']} already exists, skipping.")
            continue
        customer = Customer(
            full_name=p["full_name"],
            email=p["email"],
            summary=p["summary"],
            summary_vector=embed(p["summary"]),
            numberOfConversations=p["convos"],
        )
        session.add(customer)
        print(f"Added {p['full_name']}")
    session.commit()
