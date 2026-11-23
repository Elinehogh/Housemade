"""House rules: anyone can add one, and a majority of the flat can vote to remove it (specs/house-rules.md)."""

from datetime import date

import streamlit as st

import db
from config import REFRESH_SECONDS
from logic import MAX_RULE_LENGTH, check_can_vote_to_remove, clean_rule, has_majority, votes_needed
from screens.demo_data import MEMBERS

EXPLANATION = "Removing a rule takes a majority of the flat. Everyone gets one vote per rule, and it cannot be taken back."


def show(engine=None, user_id: int | None = None) -> None:
    """Show the rules of the user's flat. Without a login (preview), show the sample data."""
    st.subheader("📜 House rules")
    st.caption(EXPLANATION)
    # Shown here because a message from before st.rerun() would be gone after it.
    if st.session_state.pop("rule_removed", False):
        st.toast("Rule removed by majority vote.", icon="🗳️")
    if engine is None:
        _demo_rules()
        _add_form(_add_demo_rule)
    else:
        _rule_list(engine, user_id)
        _add_form(lambda text: db.add_rule(engine, user_id, text))


def cast_remove_vote(engine, user_id: int | None, rule_id: int) -> None:
    """Vote to remove a rule. Raises ValueError if this member already voted on it."""
    if engine is not None:
        removed = db.vote_to_remove(engine, user_id, rule_id)
    else:
        rules = st.session_state.demo["house_rules"]
        rule = next(r for r in rules if r["id"] == rule_id)
        check_can_vote_to_remove(rule["voters"], "You")
        rule["voters"].append("You")
        removed = has_majority(len(rule["voters"]), len(MEMBERS))
        if removed:
            rules.remove(rule)
    if removed:
        st.session_state.rule_removed = True


# The list asks the database again every few seconds, so flatmates' rules and votes show up
# without reloading (specs/live-updates.md). The add form stays outside.
@st.fragment(run_every=REFRESH_SECONDS)
def _rule_list(engine, user_id: int) -> None:
    rules = db.list_rules(engine, user_id)
    if not rules:
        st.caption("No house rules yet. Add the first one below.")
    for rule in rules:
        voted = user_id in rule["voter_ids"]
        if _show_rule(rule["id"], rule["text"], rule["who"], rule["added_at"], rule["voters"], rule["votes_needed"], voted):
            try:
                cast_remove_vote(engine, user_id, rule["id"])
                st.rerun()
            except ValueError as error:
                st.error(str(error))


def _show_rule(rule_id: int, text: str, who: str, added: date, voters: list[str], needed: int, voted: bool) -> bool:
    """Draw one rule, and return True if the vote button was clicked."""
    with st.container(border=True):
        left, right = st.columns([3, 2], vertical_alignment="center")
        with left:
            # st.text shows the rule exactly as typed, without reading it as Markdown.
            st.text(text)
            st.caption(f"Added by {who} on {added:%d %b %Y}")
            count = f"{len(voters)} of {needed} votes to remove"
            st.caption(f"{count}: {', '.join(voters)}" if voters else count)
        label = "✓ You voted" if voted else "🗳️ Vote to remove"
        return right.button(label, key=f"remove_rule_{rule_id}", disabled=voted, width="stretch")


def _add_form(add) -> None:
    with st.form("add_rule", clear_on_submit=True):
        text = st.text_input(
            "Add a rule", placeholder="Quiet after 23:00 on weekdays", max_chars=MAX_RULE_LENGTH
        )
        if st.form_submit_button("Add rule", type="primary"):
            try:
                add(text)
                st.rerun()
            except ValueError as error:
                st.error(str(error))


# --- The preview with sample data ----------------------------------------------


def _demo_rules() -> None:
    demo = st.session_state.demo
    needed = votes_needed(len(MEMBERS))
    for rule in demo["house_rules"]:
        if _show_rule(rule["id"], rule["text"], rule["who"], rule["added"], rule["voters"], needed, "You" in rule["voters"]):
            try:
                cast_remove_vote(None, None, rule["id"])
                st.rerun()
            except ValueError as error:
                st.error(str(error))
    if not demo["house_rules"]:
        st.caption("No house rules yet. Add the first one below.")


def _add_demo_rule(text: str) -> None:
    rules = st.session_state.demo["house_rules"]
    rule = clean_rule(text, [r["text"] for r in rules])
    next_id = max((r["id"] for r in rules), default=0) + 1
    rules.append({"id": next_id, "text": rule, "who": "You", "added": date.today(), "voters": []})
