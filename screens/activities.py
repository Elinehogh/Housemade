"""Activities the flat can do together: ideas for today's weather, voting, and what the fund can pay for.

The list comes from the database, or from the sample data in the preview without a login (engine is None).
"""

from datetime import date
from html import escape

import streamlit as st

import db
import services
from config import DEFAULT_PLACE, REFRESH_SECONDS
from logic import (
    MAX_ACTIVITY_COST,
    MAX_ACTIVITY_LENGTH,
    activity_cost_cents,
    can_afford,
    check_activity_date,
    check_can_remove_activity,
    check_can_vote,
    clean_activity_name,
    format_euros,
    pick_client_ip,
    rank_activities,
    rule_suggestions,
)

WEATHER_ICONS = {"sunny": "☀️", "cloudy": "⛅", "foggy": "🌫️", "rainy": "🌧️", "snowy": "❄️", "stormy": "⛈️"}
DEMO_USER = "You"


# --- Where the visitor is, and the weather there --------------------------------


@st.cache_data(ttl=3600, show_spinner=False)
def _location(ip: str | None) -> dict:
    return services.find_location(ip)


@st.cache_data(ttl=1800, show_spinner=False)
def _weather(lat: float, lon: float) -> dict:
    return services.fetch_weather(lat, lon)


def current_place() -> dict:
    """Where the visitor is, from their IP address. Lisbon if that cannot be found."""
    ip = pick_client_ip(st.context.headers.get("X-Forwarded-For"), st.context.ip_address)
    # No public address, and the visitor is not on this computer either: we cannot tell where they are.
    # (On this computer, ipinfo.io can look up the computer's own address instead.)
    if ip is None and st.context.ip_address not in (None, "127.0.0.1", "::1"):
        return DEFAULT_PLACE
    try:
        return _location(ip)
    except ValueError:
        return DEFAULT_PLACE


def weather_at(place: dict) -> dict:
    """Today's weather at a place. Raises ValueError if it is not available."""
    return _weather(round(place["lat"], 2), round(place["lon"], 2))


# --- The list: from the database, or the sample data in the preview ------------


def load(engine, user_id: int | None) -> list[dict]:
    """The flat's activities, most votes first, each with its 'votes'."""
    if engine is not None:
        return db.list_activities(engine, user_id)
    demo = st.session_state.demo
    items = [
        {
            **activity,
            "votes": [
                {"user_id": vote["who"], "name": vote["who"], "day": vote["day"]}
                for vote in demo["votes"] if vote["activity"] == activity["activity"]
            ],
        }
        for activity in demo["activities"]
    ]
    return [item for item, _ in rank_activities(items, demo["votes"])]


def add(engine, user_id: int | None, name: str, cost, planned_on: date | None) -> None:
    """Add an activity. Raises ValueError if it breaks the rules."""
    if engine is not None:
        db.add_activity(engine, user_id, name, cost, planned_on)
        return
    demo = st.session_state.demo
    check_activity_date(planned_on, date.today())
    cost_cents = activity_cost_cents(cost)
    clean = clean_activity_name(name, [activity["activity"] for activity in demo["activities"]])
    next_id = max((activity["id"] for activity in demo["activities"]), default=0) + 1
    demo["activities"].append(
        {"id": next_id, "activity": clean, "cost_cents": cost_cents, "planned_on": planned_on,
         "added_by": DEMO_USER, "who": DEMO_USER}
    )


def vote(engine, user_id: int | None, item: dict, items: list[dict]) -> None:
    """Vote for an activity. Raises ValueError if this member may not vote for it now."""
    if engine is not None:
        db.vote_for_activity(engine, user_id, item["id"])
        return
    today = date.today()
    _check_vote(item, items, DEMO_USER, today)
    st.session_state.demo["votes"].append({"activity": item["activity"], "who": DEMO_USER, "day": today})


def _remove(engine, user_id: int | None, item: dict) -> None:
    if engine is not None:
        db.remove_activity(engine, user_id, item["id"])
        return
    demo = st.session_state.demo
    check_can_remove_activity(item["added_by"], DEMO_USER, "admin")
    demo["activities"] = [a for a in demo["activities"] if a["id"] != item["id"]]
    demo["votes"] = [v for v in demo["votes"] if v["activity"] != item["activity"]]


def _balance(engine, user_id: int | None) -> int:
    """The real balance of the fund in cents, the same as on the Fund tab."""
    if engine is not None:
        return db.fund_balance(engine, user_id)
    return round(sum(entry["amount"] for entry in st.session_state.demo["fund"]) * 100)


def _check_vote(item: dict, items: list[dict], me, today: date) -> None:
    votes = [
        {"activity": other["activity"], "who": cast["user_id"], "day": cast["day"]}
        for other in items for cast in other["votes"]
    ]
    check_can_vote([other["activity"] for other in items], votes, item["activity"], me, today)


def vote_blocked(item: dict, items: list[dict], me, today: date) -> str | None:
    """Why this member cannot vote for this activity now, or None if they can."""
    try:
        _check_vote(item, items, me, today)
    except ValueError as error:
        return str(error)
    return None


def _may_remove(item: dict, me, role: str) -> bool:
    try:
        check_can_remove_activity(item["added_by"], me, role)
    except ValueError:
        return False
    return True


# --- The screen -----------------------------------------------------------------


def show(engine=None, user_id: int | None = None) -> None:
    st.subheader("🎉 Things to do together")
    _show_ideas(engine, user_id)
    if engine is None:
        _show_list(None, None)
    else:
        _live_list(engine, user_id)
    _add_form(engine, user_id)


def _show_ideas(engine, user_id: int | None) -> None:
    """Today's weather and ideas that fit it, each with a button to put it on the list."""
    place = current_place()
    try:
        weather = weather_at(place)
    except ValueError as error:
        st.info(f"{error} Ideas for today are back when it is.")
        return

    with st.container(border=True):
        st.markdown(
            f"{WEATHER_ICONS[weather['kind']]} **Today in {place['city']}:** {weather['kind']}, "
            f"{weather['temperature']:.0f}°C now, up to {weather['max_temperature']:.0f}°C, "
            f"{weather['rain_chance']}% chance of rain"
        )
        ideas = rule_suggestions(weather, [item["activity"] for item in load(engine, user_id)])
        if ideas:
            st.caption("Ideas for today's weather:")
        for i, idea in enumerate(ideas):
            cost = "free" if idea["cost"] == 0 else f"€{idea['cost']:g}"
            left, right = st.columns([4, 1], vertical_alignment="center")
            left.markdown(f"**{idea['activity']}** · {cost}  \n{idea['why']}")
            if right.button("➕ Add", key=f"add_idea_{i}", help="Add it to the list for today so people can vote"):
                try:
                    add(engine, user_id, idea["activity"], idea["cost"], date.today())
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))


# The list asks the database again every few seconds, so flatmates' activities and votes show up
# without reloading (specs/live-updates.md). The add form stays outside.
@st.fragment(run_every=REFRESH_SECONDS)
def _live_list(engine, user_id: int) -> None:
    _show_list(engine, user_id)


def _show_list(engine, user_id: int | None) -> None:
    """The flat's list, most votes first, with who voted, a vote button and a remove button."""
    today = date.today()
    items = load(engine, user_id)
    balance = _balance(engine, user_id)
    me = user_id if engine is not None else DEMO_USER
    role = db.get_membership(engine, user_id)["role"] if engine is not None else "admin"

    only_affordable = st.toggle(f"Only what the fund can pay for ({format_euros(balance)})", key="only_affordable")
    voted_today = next(
        (item["activity"] for item in items for cast in item["votes"] if cast["user_id"] == me and cast["day"] == today),
        None,
    )
    if voted_today:
        st.html(f'<p class="hm-body">✅ You voted today, for {escape(voted_today)}. You can vote again tomorrow.</p>')
    else:
        st.caption("You have 1 vote today. You can vote for each activity once.")

    shown = [item for item in items if not only_affordable or can_afford(item["cost_cents"], balance)]
    if not items:
        st.caption("Nothing on the list yet. Add the first activity below.")
    elif not shown:
        st.caption("The fund cannot pay for anything on the list yet.")
    for item in shown:
        _show_activity(engine, user_id, item, items, me, role, today)


def _show_activity(engine, user_id, item: dict, items: list[dict], me, role: str, today: date) -> None:
    activity_id = item["id"]
    cost = "Free" if item["cost_cents"] == 0 else format_euros(item["cost_cents"])
    people = [cast["name"] for cast in item["votes"]]
    count = f"{len(people)} vote" + ("" if len(people) == 1 else "s")
    who = f"{count}: {', '.join(people)}" if people else "No votes yet"

    with st.container(border=True):
        left, right = st.columns([3, 2], vertical_alignment="center")
        # Names are put through escape(), so nothing a member types ends up in the page as code.
        left.html(
            f'<p class="hm-medium">{escape(item["activity"])}</p>'
            f'<p class="hm-body">{cost}, {item["planned_on"]:%a %d %b}, added by {escape(item["who"])}</p>'
            f'<p class="hm-body">{escape(who)}</p>'
        )
        reason = vote_blocked(item, items, me, today)
        with right.container(horizontal=True, horizontal_alignment="right"):
            if st.button("👍 Vote", key=f"vote_{activity_id}", disabled=reason is not None, help=reason):
                _act(lambda: vote(engine, user_id, item, items))
            if _may_remove(item, me, role) and st.button("Remove", key=f"remove_{activity_id}"):
                st.session_state.confirm_remove = activity_id
                st.rerun()

        # Asking first is kept in the session, so the question survives the list refreshing itself.
        if st.session_state.get("confirm_remove") == activity_id:
            st.warning("Remove this activity and its votes for everyone?")
            with st.container(horizontal=True):
                if st.button("Yes, remove", key=f"confirm_{activity_id}", type="primary"):
                    st.session_state.pop("confirm_remove", None)
                    _act(lambda: _remove(engine, user_id, item))
                if st.button("Cancel", key=f"cancel_{activity_id}"):
                    st.session_state.pop("confirm_remove", None)
                    st.rerun()


def _act(action) -> None:
    """Do something to the list, then redraw it. A rule that stops it is shown as an error."""
    try:
        action()
    except ValueError as error:
        st.error(str(error))
        return
    st.rerun()


def _add_form(engine, user_id: int | None) -> None:
    today = date.today()
    with st.form("add_activity", clear_on_submit=True):
        st.markdown("**Add your own activity**")
        name = st.text_input("Activity", placeholder="Sunset at Miradouro da Graça", max_chars=MAX_ACTIVITY_LENGTH)
        price_column, date_column = st.columns(2)
        cost = price_column.number_input(
            "Price for the flat (€)", min_value=0.0, max_value=MAX_ACTIVITY_COST, step=1.0, format="%.2f"
        )
        planned_on = date_column.date_input("Date", value=today, min_value=today, format="DD/MM/YYYY")
        if st.form_submit_button("Add activity", type="primary"):
            try:
                add(engine, user_id, name, round(cost, 2), planned_on)
                st.rerun()
            except ValueError as error:
                st.error(str(error))
