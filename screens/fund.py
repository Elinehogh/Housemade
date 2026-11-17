"""The shared fund: pant money in, shared costs out, and a savings goal."""

import streamlit as st

import db
from logic import MAX_FUND_AMOUNT, clean_amount, format_euros, fund_csv, goal_progress
from screens.demo_data import MEMBERS


def show(engine=None, user_id: int | None = None) -> None:
    """Show the fund of the user's flat. Without a login (preview), show the sample data."""
    if engine is None:
        show_demo()
        return

    is_admin = db.get_membership(engine, user_id)["role"] == "admin"
    balance = db.fund_balance(engine, user_id)
    goal = db.get_fund_goal(engine, user_id)

    st.subheader("🫙 Shared fund")
    st.metric("In the fund", format_euros(balance))
    if goal:
        text = f"Saving for: {goal['name']} ({format_euros(balance)} of {format_euros(goal['cents'])})"
        st.progress(goal_progress(balance, goal["cents"]), text=text)

    with st.form("add_pant", clear_on_submit=True):
        st.write("**Add pant money**")
        amount = st.number_input("Amount (€)", min_value=0.0, max_value=float(MAX_FUND_AMOUNT), step=0.1, key="pant_amount")
        if st.form_submit_button("Add to fund"):
            try:
                db.add_pant(engine, user_id, amount)
                st.rerun()
            except ValueError as error:
                st.error(str(error))

    if is_admin:
        with st.form("take_out", clear_on_submit=True):
            st.write("**Pay for something shared**")
            what = st.text_input("What for?", placeholder="Pizza night")
            amount = st.number_input("Amount (€)", min_value=0.0, max_value=float(MAX_FUND_AMOUNT), step=0.5, key="out_amount")
            if st.form_submit_button("Take out of fund"):
                try:
                    db.take_out(engine, user_id, what, amount)
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))

        with st.expander("Savings goal"):
            with st.form("set_goal"):
                name = st.text_input("Goal", value=goal["name"] if goal else "", placeholder="Trip to Sintra")
                amount = st.number_input("Amount (€)", min_value=0.0, max_value=float(MAX_FUND_AMOUNT),
                                         value=goal["cents"] / 100 if goal else 0.0, step=5.0, key="goal_amount")
                if st.form_submit_button("Save goal"):
                    try:
                        db.set_fund_goal(engine, user_id, name, amount)
                        st.rerun()
                    except ValueError as error:
                        st.error(str(error))
    else:
        st.caption("Only the admin can take money out of the fund or set the savings goal.")

    st.write("**History**")
    history = db.fund_history(engine, user_id)
    if not history:
        st.caption("Nothing here yet. Return some bottles!")
    for entry in history:
        sign = "+" if entry["cents"] > 0 else ""
        st.write(f"{sign}{format_euros(entry['cents'])} · {entry['what']} · {entry['who']} · {entry['date']:%d %b}")
    if history:
        st.download_button("Download history (CSV)", fund_csv(history), file_name="housemade-fund.csv", mime="text/csv")


def show_demo() -> None:
    """The preview with sample data from screens/demo_data.py. Nothing is saved."""
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
