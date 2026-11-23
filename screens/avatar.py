"""Picking an avatar: an emoji on a coloured background (specs/design.md)."""

import streamlit as st

import db
from logic import AVATAR_COLORS, AVATAR_EMOJIS, avatar_label


def picker(engine, user_id: int, key: str, avatar: tuple[str, str] | None = None) -> None:
    """Emoji and colour choices with a preview, and a button that saves them. avatar: the member's current one."""
    current = avatar or (AVATAR_EMOJIS[0], AVATAR_COLORS[4])
    emoji = st.pills("Emoji", AVATAR_EMOJIS, default=current[0], required=True, key=f"{key}_emoji")
    color = st.pills(
        "Colour",
        AVATAR_COLORS,
        default=current[1],
        required=True,
        format_func=lambda c: f":{c}-background[{emoji}]",
        key=f"{key}_color",
    )
    st.markdown(f"## {avatar_label(emoji, color)}")
    if st.button("Save avatar", type="primary", key=f"{key}_save"):
        try:
            db.set_avatar(engine, user_id, emoji, color)
            st.rerun()
        except ValueError as error:
            st.error(str(error))


def with_name(name: str, avatars: dict) -> str:
    """The member's name with their avatar in front, as markdown."""
    return f"{avatar_label(*avatars.get(name, (None, None)))} **{name}**"
