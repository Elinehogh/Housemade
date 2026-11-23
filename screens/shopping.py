"""Shared shopping list, splitting what people paid for shared things, and paying back."""

import streamlit as st

import db
from screens.avatar import with_name
from logic import COMMON_ITEMS, MAX_AMOUNT_CENTS, balances, clean_amount, format_euros
from screens.demo_data import MEMBERS


def show(engine=None, user_id: int | None = None) -> None:
    """Show the shopping list and money of the user's flat. Without a login (preview), show the sample data."""
    if engine is None:
        show_demo()
        return

    # Messages from the last action survive the rerun that refreshes the page.
    for message in st.session_state.pop("shopping_messages", []):
        st.error(message)

    show_list(engine, user_id)
    st.divider()
    show_money(engine, user_id)


def _when(moment) -> str:
    return moment.strftime("%a %d %b, %H:%M")


def show_list(engine, user_id: int) -> None:
    st.subheader("🛒 Shopping list")
    items = db.list_items(engine, user_id)
    to_buy = [item for item in items if not item["bought"]]
    bought = [item for item in items if item["bought"]]

    if not to_buy:
        st.caption("Nothing to buy right now. Add something below.")
    for item in to_buy:
        left, right = st.columns([6, 1])
        if left.checkbox(item["name"], key=f"buy_{item['id']}"):
            try:
                db.mark_bought(engine, user_id, item["id"])
            except ValueError as error:
                st.session_state.shopping_messages = [str(error)]
            st.rerun()
        if right.button("🗑", key=f"remove_{item['id']}", help=f"Remove {item['name']}"):
            try:
                db.remove_item(engine, user_id, item["id"])
            except ValueError as error:
                st.session_state.shopping_messages = [str(error)]
            st.rerun()

    with st.form("add_items", clear_on_submit=True):
        on_list = {item["name"].lower() for item in to_buy}
        choices = st.multiselect(
            "Add to the list",
            [item for item in COMMON_ITEMS if item.lower() not in on_list],
            placeholder="Pick common things, or type something else",
            accept_new_options=True,
        )
        if st.form_submit_button("Add"):
            problems = []
            for name in choices:
                try:
                    db.add_item(engine, user_id, name)
                except ValueError as error:
                    problems.append(str(error))
            st.session_state.shopping_messages = problems
            st.rerun()

    if bought:
        with st.expander(f"Bought ({len(bought)})"):
            for item in bought:
                st.write(f"~~{item['name']}~~ · {item['bought_by']}, {_when(item['bought_at'])}")
            if st.button("Clear bought items"):
                db.clear_bought_items(engine, user_id)
                st.rerun()


def show_money(engine, user_id: int) -> None:
    st.subheader("💶 Shared costs")
    members = db.flat_members(engine, user_id)
    overview = db.money_overview(engine, user_id)

    with st.form("add_expense", clear_on_submit=True):
        st.write("**I paid for something for the flat**")
        left, right = st.columns([1, 2])
        amount = left.number_input("Amount (€)", min_value=0.0, max_value=MAX_AMOUNT_CENTS / 100, step=0.5, format="%.2f")
        what = right.text_input("What was it?", placeholder="Toilet paper and dish soap")
        st.caption(f"Split equally between all {len(members)} members.")
        if st.form_submit_button("Add cost"):
            try:
                db.add_expense(engine, user_id, amount, what)
                st.rerun()
            except ValueError as error:
                st.error(str(error))

    avatars = db.flat_avatars(engine, user_id)
    st.write("**Who owes what**")
    for name, cents in overview["balances"]:
        if cents > 0:
            st.markdown(f"🟢 {with_name(name, avatars)} should get back {format_euros(cents)}")
        elif cents < 0:
            st.markdown(f"🔴 {with_name(name, avatars)} owes {format_euros(-cents)}")
        else:
            st.markdown(f"⚪ {with_name(name, avatars)} is even")

    if overview["settle_up"]:
        st.write("**To settle up**")
        for payer, receiver, cents in overview["settle_up"]:
            st.write(f"- {payer} pays {receiver} {format_euros(cents)}")

    others = {member: name for member, name in members.items() if member != user_id}
    if others:
        with st.form("confirm_payment", clear_on_submit=True):
            st.write("**Someone paid me back**")
            left, right = st.columns(2)
            payer = left.selectbox("Who paid you?", list(others), format_func=others.get)
            amount = right.number_input("Amount (€)", min_value=0.0, max_value=MAX_AMOUNT_CENTS / 100, step=0.5, format="%.2f")
            st.caption("Only the person who got the money can confirm it.")
            if st.form_submit_button("Confirm payment"):
                try:
                    db.confirm_payment(engine, user_id, payer, amount)
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))

    if overview["expenses"] or overview["payments"]:
        with st.expander("History"):
            for expense in overview["expenses"]:
                st.write(f"🧾 {expense['who']} paid {format_euros(expense['cents'])} for {expense['description']} · {_when(expense['at'])}")
            for payment in overview["payments"]:
                st.write(f"✅ {payment['from']} paid {payment['to']} back {format_euros(payment['cents'])} · {_when(payment['at'])}")


def show_demo() -> None:
    """The preview with sample data from screens/demo_data.py. Nothing is saved."""
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
