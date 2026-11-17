"""Shared shopping list, and splitting what people paid for shared things."""

import streamlit as st

from logic import balances, clean_amount
from screens.demo_data import MEMBERS


def show() -> None:
    demo = st.session_state.demo
    st.subheader("🛒 Shopping list")

    for i, item in enumerate(demo["shopping"]):
        item["bought"] = st.checkbox(item["item"], value=item["bought"], key=f"shop_{i}")

    with st.form("add_item", clear_on_submit=True):
        new_item = st.text_input("Add an item", placeholder="Olive oil")
        if st.form_submit_button("Add") and new_item.strip():
            demo["shopping"].append({"item": new_item.strip(), "bought": False})
            st.rerun()

    st.subheader("💶 Who paid for shared things")
    with st.form("add_payment", clear_on_submit=True):
        who = st.selectbox("Who paid?", MEMBERS)
        amount = st.number_input("Amount (€)", min_value=0.0, step=0.5)
        if st.form_submit_button("Add payment"):
            try:
                demo["payments"].append((who, clean_amount(amount)))
                st.rerun()
            except ValueError as error:
                st.error(str(error))

    for name, balance in balances(MEMBERS, demo["payments"]).items():
        if balance > 0:
            st.write(f"**{name}** should get back €{balance:.2f}")
        elif balance < 0:
            st.write(f"**{name}** owes €{-balance:.2f}")
        else:
            st.write(f"**{name}** is even")
