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
  * SQLAlchemy models with bi‑directional relationships. 
* **Vector stores**
  * Four FAISS indices (ingredients, meal descriptions, instructions, user summaries).  OpenAI embeddings are unit‑length so cosine = inner‑product. 
* **Front‑ends**
  * `GUI.py` – shopper‑facing assistant.
  * `Sales.py` – staff dashboard with editable discount table (`st.data_editor`) and slider‑driven audience preview. 

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
| Step              | Script                                          | What it does                                                                      |
|-------------------|-------------------------------------------------|-----------------------------------------------------------------------------------|
| Crawl MealDB      | `python -m RecipeManager.Knowledge.MealCrawler` | Downloads all recipes & ingredients, adds missing vectors via the LLM.            |
| Populate shop     | `python -m RecipeManager.Knowledge.ShopManager` | Adds prices and marks **20 %** of items on sale.                                  |
| Seed dummy users  | `python main.py`                                | Inserts 20 realistic customers with embedded summaries.                           |

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
GUI.py
SalesGUI.py
README.md
main.py  # upload of dummy customers
  ...
 ```


