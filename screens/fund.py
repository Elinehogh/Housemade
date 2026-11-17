"""The shared fund: pant money in, flat activities out, and a savings goal."""

import streamlit as st

from logic import clean_amount
from screens.demo_data import MEMBERS


def show() -> None:
    demo = st.session_state.demo
    total = sum(entry["amount"] for entry in demo["fund"])
    goal_name, goal_amount = demo["fund_goal"]

    st.subheader("🫙 Shared fund")
    st.metric("In the fund", f"€{total:.2f}")
    st.progress(min(max(total / goal_amount, 0.0), 1.0), text=f"Saving for: {goal_name} (€{total:.2f} of €{goal_amount:.0f})")

    with st.form("add_pant", clear_on_submit=True):
        st.write("**Add pant money**")
        who = st.selectbox("Who returned the bottles?", MEMBERS)
        amount = st.number_input("Amount (€)", min_value=0.0, step=0.1)
        if st.form_submit_button("Add to fund"):
            try:
                demo["fund"].append({"what": "Pant", "who": who, "amount": clean_amount(amount)})
                st.rerun()
            except ValueError as error:
                st.error(str(error))

    st.write("**History**")
    for entry in reversed(demo["fund"]):
        sign = "+" if entry["amount"] > 0 else "−"
        st.write(f"{sign}€{abs(entry['amount']):.2f} · {entry['what']} · {entry['who']}")
