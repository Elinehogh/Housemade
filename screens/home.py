"""The Flat tab: an overview for the logged-in member, the invite code and the members."""

from datetime import date

import streamlit as st

import db
from config import REFRESH_SECONDS
from logic import deadline_status, format_euros, goal_progress, my_chores_summary
from screens.avatar import with_name
from screens.demo_data import MEMBERS


def show(engine, user_id: int, invite_code: str | None) -> None:
    """Show the overview of the user's flat. Without a login (engine is None), show the sample data."""
    if engine is None:
        show_demo(invite_code)
        return
    _overview(engine, user_id)
    _invite(invite_code)
    _members(engine, user_id)


# The numbers ask the database again every few seconds, like the other shared lists (specs/live-updates.md).
@st.fragment(run_every=REFRESH_SECONDS)
def _overview(engine, user_id: int) -> None:
    today = date.today()
    summary = my_chores_summary(db.list_chores(engine, user_id), user_id, today)
    mine = db.money_overview(engine, user_id)["mine"]
    fund = db.fund_balance(engine, user_id)
    goal = db.get_fund_goal(engine, user_id)
    to_buy = sum(not item["bought"] for item in db.list_items(engine, user_id))
    _show_numbers(summary, mine, fund, goal, to_buy, today)


def _show_numbers(summary: dict, mine: int, fund: int, goal: dict | None, to_buy: int, today: date) -> None:
    st.subheader("👋 Your overview")
    chores_col, points_col, money_col, fund_col = st.columns(4)
    overdue = f"{summary['overdue']} overdue" if summary["overdue"] else None
    chores_col.metric("Your chores", summary["open"], delta=overdue, delta_color="inverse", border=True)
    points_col.metric("Points this week", summary["points"], border=True)
    if mine < 0:
        money_col.metric("You owe", format_euros(-mine), border=True)
    else:
        money_col.metric("You get back", format_euros(mine), border=True)
    fund_col.metric("In the fund", format_euros(fund), border=True)

    if goal:
        st.progress(goal_progress(fund, goal["cents"]), text=f"🎯 {goal['name']}: {format_euros(fund)} of {format_euros(goal['cents'])}")

    with st.container(border=True):
        st.markdown("**Up next for you**")
        if not summary["next"]:
            st.caption("Nothing on your list. Enjoy the free time! 🎉")
        for chore in summary["next"]:
            st.write(f"• {chore['name']} · {chore['points']} pts{_deadline(chore['due_on'], today)}")
        if to_buy:
            st.caption(f"🛒 {to_buy} thing{'s' if to_buy != 1 else ''} on the shopping list.")


def _deadline(due_on, today: date) -> str:
    status = deadline_status(due_on, today)
    if status == "overdue":
        return f" · 🔴 overdue since {due_on:%a %d %b}"
    if status == "today":
        return " · 🟡 due today"
    return f" · 📅 by {due_on:%a %d %b}" if due_on else ""


def _invite(invite_code: str | None) -> None:
    if invite_code:
        st.info(f"Invite your flatmates with the code **{invite_code}**", icon="✉️")


@st.fragment(run_every=REFRESH_SECONDS)
def _members(engine, user_id: int) -> None:
    """The member list, asked again every few seconds so new flatmates show up (specs/live-updates.md)."""
    _show_members(db.list_members(engine, user_id), db.flat_avatars(engine, user_id))


def _show_members(members: list[dict], avatars: dict) -> None:
    st.markdown("**Members**")
    for member in members:
        admin = " · admin" if member["role"] == "admin" else ""
        st.markdown(f"{with_name(member['name'], avatars)}{admin}")


def show_demo(invite_code: str | None) -> None:
    """The same overview from the sample data in screens/demo_data.py."""
    demo = st.session_state.demo
    today = date.today()
    open_chores = [
        {"name": c["chore"], "points": c["points"], "due_on": None} for c in demo["chores"] if c["who"] == "You" and not c["done"]
    ]
    summary = {"open": len(open_chores), "overdue": 0, "points": demo["points"]["You"], "next": open_chores[:3]}
    fund = round(sum(entry["amount"] for entry in demo["fund"]) * 100)
    goal_name, goal_euros = demo["fund_goal"]
    paid = sum(amount for who, amount in demo["payments"] if who == "You")
    share = sum(amount for _, amount in demo["payments"]) / len(MEMBERS)
    to_buy = sum(not item["bought"] for item in demo["shopping"])
    goal = {"name": goal_name, "cents": round(goal_euros * 100)}
    _show_numbers(summary, round((paid - share) * 100), fund, goal, to_buy, today)
    _invite(invite_code)
    demo_avatars = dict(zip(MEMBERS, [("🦊", "orange"), ("🐼", "green"), ("🎸", "violet"), ("🌻", "yellow")]))
    _show_members([{"name": name, "role": "admin" if name == "You" else "member"} for name in MEMBERS], demo_avatars)
