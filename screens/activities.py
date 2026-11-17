"""Activities the flat can do together: ideas for today's weather, voting, and what the fund can pay for."""

from datetime import date

import streamlit as st

import services
from config import DEFAULT_PLACE
from logic import check_can_vote, pick_client_ip, rank_activities, rule_suggestions

WEATHER_ICONS = {"sunny": "☀️", "cloudy": "⛅", "foggy": "🌫️", "rainy": "🌧️", "snowy": "❄️", "stormy": "⛈️"}


@st.cache_data(ttl=3600, show_spinner=False)
def _location(ip: str | None) -> dict:
    return services.find_location(ip)


@st.cache_data(ttl=1800, show_spinner=False)
def _weather(lat: float, lon: float) -> dict:
    return services.fetch_weather(lat, lon)


def _place() -> dict:
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


def _show_ideas(place: dict) -> None:
    """Today's weather and ideas that fit it, each with a button to put it on the list."""
    demo = st.session_state.demo
    try:
        weather = _weather(round(place["lat"], 2), round(place["lon"], 2))
    except ValueError as error:
        st.info(f"{error} Ideas for today are back when it is.")
        return

    with st.container(border=True):
        st.markdown(
            f"{WEATHER_ICONS[weather['kind']]} **Today in {place['city']}:** {weather['kind']}, "
            f"{weather['temperature']:.0f}°C now, up to {weather['max_temperature']:.0f}°C, "
            f"{weather['rain_chance']}% chance of rain"
        )
        ideas = rule_suggestions(weather, [a["activity"] for a in demo["activities"]])
        if ideas:
            st.caption("Ideas for today's weather:")
        for i, idea in enumerate(ideas):
            cost = "free" if idea["cost"] == 0 else f"€{idea['cost']:g}"
            left, right = st.columns([4, 1], vertical_alignment="center")
            left.markdown(f"**{idea['activity']}** · {cost}  \n{idea['why']}")
            if right.button("➕ Add", key=f"add_idea_{i}", help="Add it to the list so people can vote"):
                demo["activities"].append({"activity": idea["activity"], "cost": idea["cost"]})
                st.rerun()


def _show_votes(me: str, fund: float) -> None:
    """The flat's list, most votes first, with who voted and a vote button."""
    demo = st.session_state.demo
    names = [a["activity"] for a in demo["activities"]]
    today = date.today()

    only_affordable = st.toggle(f"Only what the fund can pay for (€{fund:.2f})")
    voted_today = next((v["activity"] for v in demo["votes"] if v["who"] == me and v["day"] == today), None)
    if voted_today:
        st.caption(f"✅ You voted today, for {voted_today}. You can vote again tomorrow.")
    else:
        st.caption("You have 1 vote today. You can vote for each activity once.")
    for i, (activity, people) in enumerate(rank_activities(demo["activities"], demo["votes"])):
        if only_affordable and activity["cost"] > fund:
            continue
        name = activity["activity"]
        cost = "free" if activity["cost"] == 0 else f"€{activity['cost']:g}"
        count = f"{len(people)} vote" + ("" if len(people) == 1 else "s")
        who = ", ".join("you" if person == me else person for person in people) or "no votes yet"

        try:
            check_can_vote(names, demo["votes"], name, me, today)
            reason = None
        except ValueError as error:
            reason = str(error)

        left, right = st.columns([4, 1], vertical_alignment="center")
        left.markdown(f"**{name}** · {cost} · {count}  \n👥 {who}")
        if right.button("👍 Vote", key=f"vote_{i}", disabled=reason is not None, help=reason):
            demo["votes"].append({"activity": name, "who": me, "day": today})
            st.rerun()


def show(me: str) -> None:
    demo = st.session_state.demo
    fund = sum(entry["amount"] for entry in demo["fund"])

    st.subheader("🎉 Things to do together")
    _show_ideas(_place())
    _show_votes(me, fund)
