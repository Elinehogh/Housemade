"""The Today tab: the weather with ideas, your next chore, money, the fund and the rest of the flat in tiles."""

from datetime import date
from html import escape

import streamlit as st

import db
from config import REFRESH_SECONDS
from logic import (
    avatar_label,
    balances,
    deadline_status,
    format_euros,
    goal_progress,
    money_detail,
    money_summary,
    my_chores_summary,
    rule_suggestions,
    settle_up,
    to_buy_text,
    weather_headline,
)

from screens import activities
from screens.avatar import picker, with_name
from screens.demo_data import MEMBERS
from screens.sky import open_view

WET_WEATHER = ("rainy", "stormy")


def show(engine, user_id: int, invite_code: str | None, me: str = "You") -> None:
    """Show today's overview of the user's flat. Without a login (engine is None), show the sample data."""
    if engine is None:
        show_demo(invite_code)
        return
    _greeting(engine, user_id, me)
    _weather_tile(engine, user_id)
    _live_tiles(engine, user_id)
    _invite(invite_code)
    _members(engine, user_id)


def _greeting(engine, user_id: int, me: str) -> None:
    """The member's avatar and name, with a button to change the avatar right where they see it.

    Kept outside the refreshing tiles, so the open avatar picker does not close every few seconds.
    """
    face, hello, change = st.columns([1, 5, 3], vertical_alignment="center")
    face.markdown(f"## {avatar_label(*(db.get_avatar(engine, user_id) or (None, None)))}")
    hello.markdown(f"### Hi {me}!")
    with change.popover("Change avatar", icon=":material/face:"):
        picker(engine, user_id, key="home_avatar")


# --- The weather and ideas for today -------------------------------------------


def _weather_tile(engine, user_id: int | None) -> None:
    place = activities.current_place()
    try:
        weather = activities.weather_at(place)
    except ValueError as error:
        st.info(f"{error} Ideas for today are back when it is.")
        return

    key = "sky_hero_wet" if weather["kind"] in WET_WEATHER else "sky_hero"
    with st.container(key=key):
        left, right = st.columns([5, 6], gap="large", vertical_alignment="center")
        with left:
            st.html(f'<h2 class="hm-title">{escape(weather_headline(weather["kind"], place["city"]))}</h2>')
            st.html(f'<p class="hm-temp">{weather["temperature"]:.0f}°</p>')
            st.html(
                f'<p class="hm-body">Up to {weather["max_temperature"]:.0f}°, '
                f'{weather["rain_chance"]}% chance of rain</p>'
            )
        with right:
            st.html('<h2 class="hm-title">Good ideas for today</h2>')
            ideas = rule_suggestions(weather, [item["activity"] for item in activities.load(engine, user_id)])
            if not ideas:
                st.html('<p class="hm-body">All of today\'s ideas are already on your list.</p>')
            for i, idea in enumerate(ideas):
                cost = "Free" if idea["cost"] == 0 else f"€{idea['cost']:g}"
                with st.container(horizontal=True, wrap=False, vertical_alignment="center", key=f"idea_{i}"):
                    st.html(
                        f'<p class="hm-idea">{escape(idea["activity"])}<span>{cost}. {escape(idea["why"])}</span></p>',
                        width="stretch",
                    )
                    if st.button("Add", key=f"today_add_{i}", help="Add it to the activities so people can vote"):
                        try:
                            activities.add(engine, user_id, idea["activity"], idea["cost"], date.today())
                            st.rerun()
                        except ValueError as error:
                            st.error(str(error))


# --- The tiles -----------------------------------------------------------------


# The numbers ask the database again every few seconds, like the other shared lists (specs/live-updates.md).
@st.fragment(run_every=REFRESH_SECONDS)
def _live_tiles(engine, user_id: int) -> None:
    today = date.today()
    summary = my_chores_summary(db.list_chores(engine, user_id), user_id, today)
    money = db.money_overview(engine, user_id)
    goal = db.get_fund_goal(engine, user_id)
    to_buy = [item["name"] for item in db.list_items(engine, user_id) if not item["bought"]]
    _tiles(
        engine=engine,
        user_id=user_id,
        summary=summary,
        finish=lambda chore: db.tick_off_chore(engine, user_id, chore["id"]),
        money_cents=money["mine"],
        money_lines=money_detail(money["mine_to_pay"], money["mine_to_get"]),
        fund=db.fund_balance(engine, user_id),
        goal=goal,
        to_buy=to_buy,
        ranking=db.chores_leaderboard(engine, user_id),
        my_name=db.flat_members(engine, user_id)[user_id],
        today=today,
    )


def _tiles(engine, user_id, summary, finish, money_cents, money_lines, fund, goal, to_buy, ranking, my_name, today) -> None:
    with st.container(key="sky_grid"):
        _chore_tile(summary, finish, today)
        _money_tile(money_cents, money_lines)
        _fund_tile(fund, goal)
        with st.container(key="tile_buy"):
            _title("To buy")
            st.html(f'<p class="hm-medium">{escape(to_buy_text(to_buy))}</p>')
        with st.container(key="tile_week"):
            _title("This week")
            rows = "".join(
                f'<div class="hm-row{" me" if name == my_name else ""}"><span>{escape(name)}</span><span>{points}</span></div>'
                for name, points in ranking
            )
            st.html(rows)
        _top_activity_tile(engine, user_id, today)
        # Only the title: the rules themselves are on the House rules tab.
        if st.button("House rules", key="open_rules", on_click=open_view, args=("House rules",), width="stretch"):
            st.rerun()


def _title(text: str) -> None:
    st.html(f'<h3 class="hm-title">{escape(text)}</h3>')


def _chore_tile(summary: dict, finish, today: date) -> None:
    with st.container(key="tile_chore"):
        _title("Your turn")
        if not summary["next"]:
            st.html('<p class="hm-big">Nothing to do</p>')
            st.html('<p class="hm-body">Enjoy the free time!</p>')
            return
        chore = summary["next"][0]
        st.html(f'<p class="hm-big">{escape(chore["name"])}</p>')
        extra = _chore_note(chore["due_on"], summary, today)
        if extra:
            st.html(f'<p class="hm-body">{extra}</p>')
        if st.button(f"Done, +{chore['points']} points", key="today_done"):
            try:
                finish(chore)
                st.rerun()
            except ValueError as error:
                st.error(str(error))


def _chore_note(due_on, summary: dict, today: date) -> str:
    """When the next chore is due, and how many more the member has."""
    parts = []
    status = deadline_status(due_on, today)
    if status == "overdue":
        parts.append(f"Overdue since {due_on:%a %d %b}")
    elif status == "today":
        parts.append("Due today")
    elif due_on:
        parts.append(f"By {due_on:%a %d %b}")
    others = summary["open"] - 1
    if others:
        parts.append(f"{others} more after this")
    return ", ".join(parts)


def _money_tile(cents: int, lines: list[str]) -> None:
    title, amount = money_summary(cents)
    with st.container(key="tile_money"):
        _title(title)
        st.html(f'<p class="hm-big">{amount}</p>')
        if lines:
            st.html(f'<p class="hm-body">{"<br>".join(escape(line) for line in lines)}</p>')


def _fund_tile(fund: int, goal: dict | None) -> None:
    with st.container(key="tile_fund"):
        _title(goal["name"] if goal else "Shared fund")
        st.html(f'<p class="hm-big">{format_euros(fund)}</p>')
        if goal:
            percent = goal_progress(fund, goal["cents"]) * 100
            st.html(
                f'<p class="hm-body">of {format_euros(goal["cents"])}</p>'
                f'<span class="hm-bar" aria-hidden="true"><span style="width: {percent:.1f}%"></span></span>'
            )


def _top_activity_tile(engine, user_id: int | None, today: date) -> None:
    items = activities.load(engine, user_id)
    with st.container(key="tile_top"):
        _title("Top activity")
        if not items:
            st.html('<p class="hm-body">Nothing on the list yet.</p>')
            return
        top = items[0]
        count = f"{len(top['votes'])} vote" + ("" if len(top["votes"]) == 1 else "s")
        st.html(f'<p class="hm-medium">{escape(top["activity"])}</p><p class="hm-body">{count}</p>')
        me = user_id if engine is not None else activities.DEMO_USER
        reason = activities.vote_blocked(top, items, me, today)
        if st.button("Vote", key="today_vote", disabled=reason is not None, help=reason):
            try:
                activities.vote(engine, user_id, top, items)
                st.rerun()
            except ValueError as error:
                st.error(str(error))


# --- The flat ------------------------------------------------------------------


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


# --- The preview with sample data ----------------------------------------------


def show_demo(invite_code: str | None) -> None:
    """The same overview from the sample data in screens/demo_data.py."""
    demo = st.session_state.demo
    today = date.today()
    open_chores = [
        {"name": c["chore"], "points": c["points"], "due_on": None, "index": i}
        for i, c in enumerate(demo["chores"])
        if c["who"] == "You" and not c["done"]
    ]
    summary = {"open": len(open_chores), "overdue": 0, "points": demo["points"]["You"], "next": open_chores[:3]}

    def finish(chore: dict) -> None:
        demo["chores"][chore["index"]]["done"] = True
        demo["points"]["You"] += chore["points"]

    owed = {name: round(cents * 100) for name, cents in balances(MEMBERS, demo["payments"]).items()}
    transfers = settle_up(owed)
    to_pay = [(to, cents) for payer, to, cents in transfers if payer == "You"]
    to_get = [(frm, cents) for frm, to, cents in transfers if to == "You"]
    goal_name, goal_euros = demo["fund_goal"]
    ranking = sorted(demo["points"].items(), key=lambda item: (-item[1], item[0]))

    _weather_tile(None, None)
    _tiles(
        engine=None,
        user_id=None,
        summary=summary,
        finish=finish,
        money_cents=owed["You"],
        money_lines=money_detail(to_pay, to_get),
        fund=round(sum(entry["amount"] for entry in demo["fund"]) * 100),
        goal={"name": goal_name, "cents": round(goal_euros * 100)},
        to_buy=[item["item"] for item in demo["shopping"] if not item["bought"]],
        ranking=ranking,
        my_name="You",
        today=today,
    )
    _invite(invite_code)
    demo_avatars = dict(zip(MEMBERS, [("🦊", "orange"), ("🐼", "green"), ("🎸", "violet"), ("🌻", "yellow")]))
    _show_members([{"name": name, "role": "admin" if name == "You" else "member"} for name in MEMBERS], demo_avatars)
