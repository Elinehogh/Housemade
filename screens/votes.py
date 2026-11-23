"""The Needs your vote tile at the top of Today: every vote waiting for this member (specs/votes-waiting.md)."""

import re
from datetime import date
from html import escape

import streamlit as st

from logic import votes_needed, votes_waiting, week_start
from screens import activities, house_rules, prizes
from screens.demo_data import MEMBERS
from screens.sky import open_view

# Button labels are read as Markdown, so these characters are escaped to show a member's text exactly as typed.
MARKDOWN_CHARACTERS = re.compile(r"([\\`*_{}\[\]()#+\-.!~:$|<>])")


def _plain(text: str) -> str:
    return MARKDOWN_CHARACTERS.sub(r"\\\1", text)


def _safe_key(key: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "_", key)


def show(engine, user_id, me, prize_options: dict, items: list[dict], rules: list[dict], needed: int, today: date) -> None:
    """Show what is waiting for this member. items is the flat's activities, as on the Activities tab."""
    # Shown here because a message from before st.rerun() would be gone after it.
    if st.session_state.pop("rule_removed", False):
        st.toast("Rule removed by majority vote.", icon="🗳️")

    # Not now lasts for this visit only, so nothing is hidden for good.
    skipped = st.session_state.setdefault("skipped_votes", set())
    waiting = votes_waiting(prize_options, items, rules, me, today, needed, skipped)
    if not waiting:
        st.html('<p class="hm-caught-up">✅ Nothing is waiting for your vote.</p>')
        return

    with st.container(key="tile_votes"):
        st.html(f'<h2 class="hm-title">Needs your vote ({len(waiting)})</h2>')
        for item in waiting:
            _card(engine, user_id, item, items, skipped, today)


def show_demo(items: list[dict], today: date) -> None:
    """The same tile from the sample data in screens/demo_data.py."""
    demo = st.session_state.demo
    monday = week_start(today)
    prize_options = {
        kind: [
            {"id": p["id"], "name": p["name"], "votes": [{"user_id": n, "name": n} for n in p["votes"]]}
            for p in demo["prizes"] if p["week"] == monday and p["kind"] == kind
        ]
        for kind in ("winner", "loser")
    }
    rules = [
        {"id": r["id"], "text": r["text"], "voters": list(r["voters"]), "voter_ids": list(r["voters"])}
        for r in demo["house_rules"] if r["voters"]
    ]
    show(None, None, "You", prize_options, items, rules, votes_needed(len(MEMBERS)), today)


def _card(engine, user_id, item: dict, items: list[dict], skipped: set, today: date) -> None:
    key = _safe_key(item["key"])
    with st.container(key=f"votecard_{key}"):
        # Names and rules are put through escape(), so nothing a member types ends up in the page as code.
        st.html(
            f'<p class="hm-vote-question">{escape(item["question"])}</p>'
            f'<p class="hm-vote-note">{escape(item["note"])}</p>'
        )
        with st.container(horizontal=True, vertical_alignment="center"):
            for choice in item["choices"]:
                label = _plain(choice["label"])
                if item["type"] != "rule":
                    label += f" \\({choice['votes']}\\)"
                # wrap: a long suggestion goes onto a second line on a phone instead of being cut off.
                if st.button(label, key=f"waiting_{key}_{choice['id']}", wrap=True):
                    try:
                        _cast(engine, user_id, item, choice, items, today)
                        st.rerun()
                    except ValueError as error:
                        st.error(str(error))
            if item["more"] and st.button(
                f"See {item['more']} more", key=f"more_{key}", type="tertiary",
                on_click=open_view, args=("Activities",),
            ):
                st.rerun()
            if st.button("Not now", key=f"skip_{key}", type="tertiary"):
                skipped.add(item["key"])
                st.rerun()


def _cast(engine, user_id, item: dict, choice: dict, items: list[dict], today: date) -> None:
    if item["type"] == "prize":
        prizes.cast_vote(engine, user_id, choice["id"], today)
    elif item["type"] == "rule":
        house_rules.cast_remove_vote(engine, user_id, choice["id"])
    else:
        activity = next(other for other in items if other["id"] == choice["id"])
        activities.vote(engine, user_id, activity, items)
