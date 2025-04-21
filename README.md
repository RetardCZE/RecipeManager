# RecipeManager 🍳🛒

> **DISCLAIMER** – this codebase was created in a _pair‑programming_ workflow with ChatGPT.  
> Lines, ideas and even bugs have human + LLM authorship.

## Overview
RecipeManager is a compact demo‑stack that shows how OpenAI function‑calling, FAISS vector search and a Streamlit GUI can power an end‑to‑end **recipe recommendation + basket builder**.

* **LLM agents**
  * `UserSessionAgent` – chats with a single shopper, suggests meals, keeps a live basket, writes purchases on checkout.
  * `SaleEventAgent` – runs when staff publish new discounts; finds meals with high _sale‑coverage_ and delivers vectors for audience targeting.
* **Data layer**
  * SQLite DB (`meal_db.db`) with Meals, Ingredients, ShopItems, Customers & Purchases.
  * SQLAlchemy models with bi‑directional relationships. :contentReference[oaicite:7]{index=7}
* **Vector stores**
  * Four FAISS indices (ingredients, meal descriptions, instructions, user summaries).  OpenAI embeddings are unit‑length so cosine = inner‑product. :contentReference[oaicite:8]{index=8}
* **Front‑ends**
  * `streamlit_chat_app.py` – shopper‑facing assistant.
  * `sale_manager_app.py` – staff dashboard with editable discount table (`st.data_editor`) and slider‑driven audience preview. :contentReference[oaicite:9]{index=9}

---

## Quick start

### 1 · Clone & install

```bash
git clone <repo>
cd RecipeManager
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt      # includes streamlit, sqlalchemy, faiss‑cpu, openai, requests
export OPENAI_API_KEY=sk‑...
```
### 2 · Ingest data
| Step              | Script                                                       | What it does                                                                      |
|-------------------|--------------------------------------------------------------|-----------------------------------------------------------------------------------|
| Crawl MealDB      | `python -m RecipeManager.Knowledge.MealCrawler`              | Downloads all recipes & ingredients, adds missing vectors via the LLM.            |
| Populate shop     | `python -m RecipeManager.Knowledge.ShopManager`              | Adds prices and marks **20 %** of items on sale.                                  |
| Seed dummy users  | `python scripts/add_dummy_customers_20diverse.py`            | Inserts 20 realistic customers with embedded summaries.                           |

*Each step is idempotent; reruns skip existing rows.*

Each step is idempotent; reruns skip existing rows.

### 3 · Run apps (PyCharm or CLI)

 - Chat assistant

```bash
streamlit run streamlit_chat_app.py
```
 - Sale manager

```bash
streamlit run sale_manager_app.py
```
PyCharm: create two “Streamlit” run configurations pointing at the above entry‑points.

## Folder layout
```bash
RecipeManager/
  Agent/              # LLM agents + VectorStore
  Knowledge/          # DB models, crawler, shop tools
  streamlit_chat_app.py
  sale_manager_app.py
scripts/
  add_dummy_customers_20diverse.py
  ...
 ```


