"""Chores: who does what, ticking off, and this week's points leaderboard."""

import streamlit as st

import db
from logic import COMMON_CHORES, MAX_POINTS, MIN_POINTS, suggested_points

MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}


def show(engine=None, user_id: int | None = None) -> None:
    """Show the chores of the user's flat. Without a login (preview), show the sample data."""
    if engine is None:
        show_demo()
        return

    st.subheader("🧹 Chores")
    chores = db.list_chores(engine, user_id)
    if not chores:
        st.caption("No chores yet. Add the first one below.")
    for chore in chores:
        label = f"{chore['name']} · {chore['who']} · {chore['points']} pts"
        mine = chore["assigned_to"] == user_id
        # A new key once the chore is done, so Streamlit draws a fresh, ticked box.
        key = f"chore_{chore['id']}_{'done' if chore['done'] else 'open'}"
        ticked = st.checkbox(label, value=chore["done"], key=key, disabled=chore["done"] or not mine)
        if ticked and not chore["done"]:
            try:
                db.tick_off_chore(engine, user_id, chore["id"])
                st.rerun()
            except ValueError as error:
                st.error(str(error))
    st.caption("You can only tick off chores that are given to you.")

    members = db.flat_members(engine, user_id)
    with st.container(border=True):
        st.write("**Add a chore**")
        name = st.selectbox(
            "Chore",
            list(COMMON_CHORES),
            index=None,
            key="new_chore",
            placeholder="Pick a common chore, or type your own",
            accept_new_options=True,
        )
        # The key follows the chore, so the points jump to the suggestion when another chore is picked.
        st.number_input(
            "Points",
            min_value=MIN_POINTS,
            max_value=MAX_POINTS,
            value=suggested_points(name),
            step=1,
            key=f"new_points_{name}",
        )
        st.selectbox("Who should do it?", list(members), format_func=members.get, key="new_chore_who")
        st.button("Add chore", on_click=_add_chore, args=(engine, user_id))
        if "chore_error" in st.session_state:
            st.error(st.session_state.pop("chore_error"))

    st.subheader("🏆 Leaderboard this week")
    for place, (name, points) in enumerate(db.chores_leaderboard(engine, user_id), start=1):
        st.write(f"{MEDALS.get(place, '  ')} **{name}**: {points} points")
    st.caption("This week's winner picks the next flat activity.")


def _add_chore(engine, user_id: int) -> None:
    """Save the chore from the form. Runs before the page is drawn again, so the form can be cleared."""
    name = st.session_state.get("new_chore") or ""
    points = st.session_state.get(f"new_points_{st.session_state.get('new_chore')}", suggested_points(name))
    try:
        db.add_chore(engine, user_id, name, points, st.session_state.get("new_chore_who"))
        st.session_state.new_chore = None
    except ValueError as error:
        st.session_state.chore_error = str(error)


def show_demo() -> None:
    """The preview with sample data from screens/demo_data.py. Nothing is saved."""
    demo = st.session_state.demo
    st.subheader("🧹 Chores this week")

    for i, chore in enumerate(demo["chores"]):
        label = f"{chore['chore']} · {chore['who']} · {chore['points']} pts"
        done = st.checkbox(label, value=chore["done"], key=f"chore_{i}", disabled=chore["done"])
        if done and not chore["done"]:
            chore["done"] = True
            demo["points"][chore["who"]] += chore["points"]
            st.rerun()

    st.subheader("🏆 Leaderboard")
    ranking = sorted(demo["points"].items(), key=lambda item: item[1], reverse=True)
    for place, (name, points) in enumerate(ranking, start=1):
        st.write(f"{MEDALS.get(place, '  ')} **{name}**: {points} points")
    st.caption("This week's winner picks the next flat activity.")
