"""
Sale Manager GUI
================
Run with:
    streamlit run sale_manager_app.py
"""

import json
import numpy as np
import streamlit as st
from sqlalchemy import update

from RecipeManager.Knowledge.models import get_session, Ingredient, ShopItem, Customer
from RecipeManager.Agent.SaleEventAgent import SaleEventAgent
from RecipeManager.Agent.VectorStore import UserSummaryVS

# ─────────────────────────────────────────────────────────────────────────────
# Utility: fetch ingredient grid  (id, name, on_sale, discount)
def fetch_grid(session):
    rows = (
        session.query(
            Ingredient.id,
            Ingredient.name,
            ShopItem.on_sale,
            ShopItem.discount,
            ShopItem.price,
        )
        .join(ShopItem, ShopItem.ingredient_id == Ingredient.id)
        .all()
    )
    return [
        {
            "id": r.id,
            "name": r.name,
            "on_sale": bool(r.on_sale),
            "discount": r.discount or 0.0,
            "price": r.price,
        }
        for r in rows
    ]


def persist_discount_changes(session, edited_rows):
    for row in edited_rows:
        stmt = (
            update(ShopItem)
            .where(ShopItem.ingredient_id == row["id"])
            .values(on_sale=row["on_sale"], discount=float(row["discount"]))
        )
        session.execute(stmt)
    session.commit()


# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Sale Manager", layout="wide")

with get_session() as session:
    if "grid_data" not in st.session_state:
        st.session_state.grid_data = fetch_grid(session)

# ------------------ Discount editor -----------------------------------------
with st.form("discount_editor"):
    st.subheader("Edit discounts")
    edited = st.data_editor(
        st.session_state.grid_data,
        column_config={
            "on_sale": st.column_config.CheckboxColumn("Sale?"),
            "discount": {"label": "Discount %", "width": 80},
            "id": {"disabled": True},
            "price": {"disabled": True},
        },
        height=480,  # scrollable  :contentReference[oaicite:8]{index=8}
        use_container_width=True,
        num_rows="fixed",
        key="discount_grid",
    )
    save_clicked = st.form_submit_button("Save discounts")
if save_clicked:
    with get_session() as session:
        persist_discount_changes(session, edited)
    st.session_state.grid_data = edited
    st.toast("Discounts saved ✅")

st.divider()

# ------------------ Publish sale & run agent --------------------------------
if st.button("Publish sale & generate recipes"):
    with st.spinner("Running sale pipeline…"):
        with get_session() as session:
            agent = SaleEventAgent(session, top_n=10)
            result = agent.run()
            st.session_state.agent_result = result

# ------------------ Audience explorer ---------------------------------------
if "agent_result" in st.session_state:
    meals = st.session_state.agent_result["meals"]
    qvecs = st.session_state.agent_result["user_query_vectors"]

    st.subheader("Top recipes by sale coverage")
    st.dataframe(meals, hide_index=True, use_container_width=True)

    st.subheader("Audience preview")
    threshold = st.slider("User‑similarity threshold", 0.0, 1.0, 0.3, 0.05)

    # --- build user‑meal mapping once per slider change ---------------------
    with st.spinner("Filtering users…"):
        with get_session() as session:
            # **NEW** fetch id → name mapping
            id2name = dict(session.query(Customer.id, Customer.full_name).all())

            vs = UserSummaryVS(session, openai_client=None)
            audience = {}
            for m in meals:
                qvec = np.asarray(qvecs[m["meal_id"]], dtype="float32").reshape(1, -1)
                scores, idxs = vs._index.search(qvec, len(vs._ids))
                users = [
                    {  # **changed keys**
                        "customer_name": id2name[vs._ids[i]],
                        "score": float(scores[0][rank]),
                    }
                    for rank, i in enumerate(idxs[0])
                    if i != -1 and scores[0][rank] >= threshold
                ]
                audience[m["name"]] = users

    # ---- flatten for display ------------------------------------------------
    flat = [
        {"meal": meal, "customer": u["customer_name"], "score": u["score"]}
        for meal, lst in audience.items()
        for u in lst
    ]
    st.dataframe(flat, hide_index=True, use_container_width=True)

    # ------------ send emails modal ---------------------------------
    @st.dialog("Send sale emails?")
    def confirm_send(payload):
        st.write(f"Meals: {len(meals)}")
        st.write(f"Total recipients: {len(flat)}")
        if st.button("Dispatch & reset"):
            # (email sending would go here)
            st.toast("Dispatched! 🎉")
            st.session_state.clear()  # reset app
            st.rerun()

    if st.button("Send emails"):
        confirm_send(flat)
