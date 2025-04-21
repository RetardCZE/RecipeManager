"""
Run with:
    streamlit run streamlit_chat_app.py
"""

import streamlit as st
from sqlalchemy import select
from RecipeManager.Knowledge.models import get_session, Customer
from RecipeManager.Agent.UserSessionAssistant import UserSessionAgent
import os
import time

# ── DB helpers ────────────────────────────────────────────────────
def list_customers(session):
    return [row[0] for row in session.execute(select(Customer.full_name)).all()]

def get_customer_summary(session, name):
    cust = session.execute(
        select(Customer.summary).where(Customer.full_name == name)
    ).scalar_one_or_none()
    return cust or "_No summary yet_"

# ── Streamlit state setup ─────────────────────────────────────────
if "customer" not in st.session_state:
    with get_session() as s:
        st.session_state.customer = list_customers(s)[0]

if "agent" not in st.session_state:
    with get_session() as s:
        st.session_state.agent = UserSessionAgent(
            api_key=os.environ["OPENAI_API_KEY"],
            user_name=st.session_state.customer,
            session=s
        )

# ── Sidebar ───────────────────────────────────────────────────────
with st.sidebar:
    with get_session() as s:
        customers = list_customers(s)
    chosen = st.selectbox("Customer", customers, index=customers.index(st.session_state.customer))
    if chosen != st.session_state.customer:
        st.toast(f"Switched to {chosen} 👤")        # 📣 streamlit toast :contentReference[oaicite:0]{index=0}
        st.session_state.customer = chosen
        with get_session() as s:
            st.session_state.agent = UserSessionAgent(
                api_key=os.environ["OPENAI_API_KEY"],
                user_name=chosen,
                session=s
            )

    st.markdown("### Profile")
    with get_session() as s:
        st.markdown(get_customer_summary(s, st.session_state.customer))

    # Basket table
    agent = st.session_state.agent
    basket_items = {i.name: agent.customer_session.basket.count(i) for i in agent.customer_session.basket}
    st.markdown("### Basket")
    if basket_items:
        st.table([(n, q) for n, q in basket_items.items()])
    else:
        st.write("_Empty_")

    disabled = not bool(agent.customer_session.basket)
    if st.button("Checkout", disabled=disabled):
        with st.spinner("Finalising checkout…"):  # spinner docs :contentReference[oaicite:3]{index=3}
            payload = agent.checkout()  # ← new method


        # -------- confirmation modal -------------------------------
        @st.dialog("Checkout complete!")  # modal API :contentReference[oaicite:4]{index=4}
        def show_receipt(data):
            st.markdown("### Purchased items")
            st.table(data["purchases"])
            st.markdown("### Updated profile summary")
            st.write(data["new_summary"])

            if st.button("Close & restart session"):
                st.session_state.clear()  # wipe memory  :contentReference[oaicite:5]{index=5}
                st.rerun(scope="app")  # full reload  :contentReference[oaicite:6]{index=6}


        show_receipt(payload)

# ── Main chat column ──────────────────────────────────────────────
st.title("🧑‍🍳 RecipeManager Chat")

for msg in agent.history:
    if msg["role"] in {"user", "assistant"}:
        if not msg['content']:
            continue
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

prompt = st.chat_input("Ask me what to cook!")               # chat_input docs :contentReference[oaicite:2]{index=2}
if prompt:
    with st.spinner("Thinking…"):                            # spinner docs :contentReference[oaicite:3]{index=3}
        agent.add_user_message(prompt)
    st.rerun()
