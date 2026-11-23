"""The weekly prize under the leaderboard: what the winner gets and what the loser has to do (specs/weekly-prize.md).

The options come from the database, or from the sample data in the preview without a login (engine is None).
"""

from datetime import date, timedelta
from html import escape

import streamlit as st

import db
from config import REFRESH_SECONDS
from logic import (
    COMMON_PRIZES,
    PRIZE_KINDS,
    check_can_suggest_prize,
    check_can_vote_prize,
    chosen_prize,
    clean_prize,
    voting_is_open,
    week_result,
    week_start,
)
from screens.safe import database_guard

TITLES = {"winner": "Winner gets", "loser": "Loser has to"}
FORM_LABELS = {"winner": "Suggest what the winner gets", "loser": "Suggest what the loser has to do"}
DEMO_USER = "You"


# --- The data: from the database, or the sample data in the preview ------------


def _load(engine, user_id: int | None, today: date) -> dict:
    if engine is not None:
        return db.prize_overview(engine, user_id, today)
    demo = st.session_state.demo
    monday = week_start(today)

    def of(week: date, kind: str) -> list[dict]:
        found = [
            {**prize, "votes": [{"user_id": name, "name": name} for name in prize["votes"]]}
            for prize in demo["prizes"] if prize["week"] == week and prize["kind"] == kind
        ]
        return sorted(found, key=lambda option: (-len(option["votes"]), option["id"]))

    def prize_name(week: date, kind: str) -> str | None:
        chosen = chosen_prize(of(week, kind))
        return chosen["name"] if chosen else None

    last_monday = monday - timedelta(days=7)
    ranking = sorted(demo["last_week_points"].items(), key=lambda item: (-item[1], item[0]))
    return {
        "week": monday,
        "voting_open": voting_is_open(today),
        "options": {kind: of(monday, kind) for kind in PRIZE_KINDS},
        "chosen": {kind: chosen_prize(of(monday, kind)) for kind in PRIZE_KINDS},
        "last_week": {
            **week_result(ranking),
            "winner_prize": prize_name(last_monday, "winner"),
            "loser_prize": prize_name(last_monday, "loser"),
        },
    }


def _suggest(engine, user_id: int | None, kind: str, text: str, today: date) -> None:
    if engine is not None:
        db.add_prize(engine, user_id, kind, text, today=today)
        return
    demo = st.session_state.demo
    monday = week_start(today)
    existing = [p["name"] for p in demo["prizes"] if p["week"] == monday and p["kind"] == kind]
    check_can_suggest_prize(kind, len(existing), today)
    name = clean_prize(text, existing)
    next_id = max((p["id"] for p in demo["prizes"]), default=0) + 1
    demo["prizes"].append({"id": next_id, "week": monday, "kind": kind, "name": name, "who": DEMO_USER, "votes": []})


def cast_vote(engine, user_id: int | None, option_id: int, today: date) -> None:
    """Vote for an option. Raises ValueError if this member may not vote for it now."""
    if engine is not None:
        db.vote_prize(engine, user_id, option_id, today=today)
        return
    prizes = st.session_state.demo["prizes"]
    prize = next(p for p in prizes if p["id"] == option_id)
    already_voted = any(
        DEMO_USER in p["votes"] for p in prizes if p["week"] == prize["week"] and p["kind"] == prize["kind"]
    )
    check_can_vote_prize(prize["week"], already_voted, today)
    prize["votes"].append(DEMO_USER)


# --- The screen -----------------------------------------------------------------


def show(engine=None, user_id: int | None = None, today: date | None = None) -> None:
    """The weekly prize. today can be set to try another day of the week."""
    st.subheader("🎁 This week's prize")
    if engine is None:
        _show_votes(None, None, today or date.today())
    else:
        _live_votes(engine, user_id, today)
    if voting_is_open(today or date.today()):
        _suggest_forms(engine, user_id, today or date.today())


# Votes and suggestions from flatmates show up without reloading (specs/live-updates.md).
# The suggestion forms stay outside, so what someone is typing is not lost.
@st.fragment(run_every=REFRESH_SECONDS)
@database_guard()
def _live_votes(engine, user_id: int, today: date | None) -> None:
    _show_votes(engine, user_id, today or date.today())


def _show_votes(engine, user_id: int | None, today: date) -> None:
    data = _load(engine, user_id, today)
    me = user_id if engine is not None else DEMO_USER

    _last_week(data["last_week"])
    if data["voting_open"]:
        st.caption("Vote until Wednesday. You get one vote for the winner and one for the loser.")
    else:
        st.caption("Voting is closed. This is the deal for this week. New vote on Monday.")

    columns = st.columns(2)
    for column, kind in zip(columns, PRIZE_KINDS):
        with column, st.container(key=f"tile_prize_{kind}"):
            st.html(f'<h3 class="hm-title">{TITLES[kind]}</h3>')
            if data["voting_open"]:
                _open_vote(engine, user_id, kind, data["options"][kind], me, today)
            else:
                _closed_vote(data["chosen"][kind])


def _open_vote(engine, user_id, kind: str, options: list[dict], me, today: date) -> None:
    if not options:
        st.html('<p class="hm-body">No suggestions yet. Add one below.</p>')
    my_vote = next((o["id"] for o in options for cast in o["votes"] if cast["user_id"] == me), None)
    for option in options:
        people = [cast["name"] for cast in option["votes"]]
        count = f"{len(people)} vote" + ("" if len(people) == 1 else "s")
        who = f"{count}: {', '.join(people)}" if people else "No votes yet"
        with st.container(horizontal=True, wrap=False, vertical_alignment="center", key=f"idea_prize_{option['id']}"):
            # Names are put through escape(), so nothing a member types ends up in the page as code.
            st.html(f'<p class="hm-idea">{escape(option["name"])}<span>{escape(who)}</span></p>', width="stretch")
            label = "✓ Voted" if option["id"] == my_vote else "Vote"
            if st.button(label, key=f"prize_vote_{option['id']}", disabled=my_vote is not None):
                try:
                    cast_vote(engine, user_id, option["id"], today)
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))


def _closed_vote(chosen: dict | None) -> None:
    if chosen is None:
        st.html('<p class="hm-medium">No deal this week</p><p class="hm-body">Nobody voted in time.</p>')
        return
    count = len(chosen["votes"])
    st.html(
        f'<p class="hm-medium">{escape(chosen["name"])}</p>'
        f'<p class="hm-body">{count} vote{"" if count == 1 else "s"}</p>'
    )


def _names(names: list[str]) -> str:
    """'Ana', 'Ana and Ben', or 'Ana, Ben and Cleo'."""
    if len(names) < 2:
        return "".join(names)
    return f"{', '.join(names[:-1])} and {names[-1]}"


def _last_week(result: dict) -> None:
    if not result["winners"]:
        return
    won = f'<strong>{escape(_names(result["winners"]))}</strong> won'
    lost = f'<strong>{escape(_names(result["losers"]))}</strong> came last'
    won += f': {escape(result["winner_prize"])}' if result["winner_prize"] else ""
    lost += f': {escape(result["loser_prize"])}' if result["loser_prize"] else ""
    with st.container(key="tile_prize_last"):
        st.html(f'<h3 class="hm-title">Last week</h3><p class="hm-body">{won}<br>{lost}</p>')


def _suggest_forms(engine, user_id: int | None, today: date) -> None:
    for column, kind in zip(st.columns(2), PRIZE_KINDS):
        with column, st.form(f"suggest_prize_{kind}", clear_on_submit=True):
            text = st.selectbox(
                FORM_LABELS[kind],
                COMMON_PRIZES[kind],
                index=None,
                placeholder="Pick an idea, or type your own",
                accept_new_options=True,
                key=f"new_prize_{kind}",
            )
            if st.form_submit_button("Suggest", width="stretch"):
                try:
                    _suggest(engine, user_id, kind, text or "", today)
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))
