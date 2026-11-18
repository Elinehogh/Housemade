"""Chores: who does what and by when, ticking off, logging what you did, and this week's leaderboard."""

from datetime import date

import streamlit as st

import db
from config import REFRESH_SECONDS
from logic import (
    COMMON_CHORES,
    MAX_POINTS,
    MIN_POINTS,
    deadline_status,
    done_before_this_week,
    suggested_points,
)

MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}

# Choices for when a new chore should be done.
DEADLINE, NO_DEADLINE, DONE_NOW = "Deadline", "No deadline", "I just did it"
WHEN_OPTIONS = (DEADLINE, NO_DEADLINE, DONE_NOW)


def show(engine=None, user_id: int | None = None) -> None:
    """Show the chores of the user's flat. Without a login (preview), show the sample data."""
    if engine is None:
        show_demo()
        return

    _to_do(engine, user_id)
    show_add_form(engine, user_id, date.today())
    _done_and_leaderboard(engine, user_id)


# The lists and the leaderboard ask the database again every few seconds, so chores added or
# ticked off by flatmates show up without reloading (specs/live-updates.md). The add form stays
# outside, so what someone is typing is not lost.
@st.fragment(run_every=REFRESH_SECONDS)
def _to_do(engine, user_id: int) -> None:
    today = date.today()
    open_chores = [c for c in db.list_chores(engine, user_id) if not c["done"]]

    st.subheader("🧹 To do")
    if not open_chores:
        st.caption("Nothing to do right now. Add a chore below.")
    for chore in open_chores:
        mine = chore["assigned_to"] == user_id
        label = f"{chore['name']} · {chore['who']} · {chore['points']} pts{_deadline_text(chore['due_on'], today)}"
        if st.checkbox(label, key=f"chore_{chore['id']}", disabled=not mine):
            try:
                db.tick_off_chore(engine, user_id, chore["id"])
            except ValueError as error:
                st.session_state.chore_error = str(error)
            st.rerun()
    if open_chores:
        st.caption("You can only tick off chores that are given to you.")


@st.fragment(run_every=REFRESH_SECONDS)
def _done_and_leaderboard(engine, user_id: int) -> None:
    today = date.today()
    done = [c for c in db.list_chores(engine, user_id) if c["done"]]
    this_week = [c for c in done if not done_before_this_week(c["done_at"], today)]
    history = [c for c in done if done_before_this_week(c["done_at"], today)]

    st.subheader("✅ Done this week")
    if not this_week:
        st.caption("Nothing done yet this week.")
    for chore in this_week:
        st.write(f"~~{chore['name']}~~ · {chore['who']} · {chore['points']} pts · {_when(chore['done_at'])}")

    st.subheader("🏆 Leaderboard this week")
    for place, (name, points) in enumerate(db.chores_leaderboard(engine, user_id), start=1):
        st.write(f"{MEDALS.get(place, '  ')} **{name}**: {points} points")
    st.caption("This week's winner picks the next flat activity.")

    if history:
        with st.expander(f"History ({len(history)})"):
            for chore in history:
                st.write(f"{chore['name']} · {chore['who']} · {chore['points']} pts · {_when(chore['done_at'])}")


def show_add_form(engine, user_id: int, today: date) -> None:
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
        when = st.radio("When?", WHEN_OPTIONS, horizontal=True, key="new_chore_when")
        if when == DEADLINE:
            st.date_input("Deadline", value=today, min_value=today, key="new_chore_due", format="DD/MM/YYYY")
        if when != DONE_NOW:
            st.selectbox("Who should do it?", list(members), format_func=members.get, key="new_chore_who")
        st.button("Add chore", type="primary", on_click=_add_chore, args=(engine, user_id))
        if "chore_error" in st.session_state:
            st.error(st.session_state.pop("chore_error"))


def _deadline_text(due_on, today: date) -> str:
    if due_on is None:
        return ""
    status = deadline_status(due_on, today)
    if status == "overdue":
        return f" · 🔴 overdue since {due_on:%a %d %b}"
    if status == "today":
        return " · 🟡 due today"
    return f" · 📅 by {due_on:%a %d %b}"


def _when(moment) -> str:
    return f"{moment:%a %d %b, %H:%M}"


def _add_chore(engine, user_id: int) -> None:
    """Save the chore from the form. Runs before the page is drawn again, so the form can be cleared."""
    state = st.session_state
    name = state.get("new_chore") or ""
    points = state.get(f"new_points_{state.get('new_chore')}", suggested_points(name))
    when = state.get("new_chore_when", DEADLINE)
    try:
        if when == DONE_NOW:
            db.log_chore(engine, user_id, name, points)
        else:
            due_on = state.get("new_chore_due") if when == DEADLINE else None
            db.add_chore(engine, user_id, name, points, state.get("new_chore_who"), due_on=due_on)
        state.new_chore = None
    except ValueError as error:
        state.chore_error = str(error)


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
