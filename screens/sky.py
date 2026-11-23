"""The Sky look: the stylesheet and moving between tabs (specs/design.md)."""

from pathlib import Path

import streamlit as st

VIEWS = ("Today", "Chores", "Shopping", "Fund", "Activities", "House rules")


def apply() -> None:
    """Add the stylesheet. Its colours follow Streamlit's light or dark theme by themselves."""
    st.html(Path(__file__).with_name("sky.css"))


def open_view(view: str) -> None:
    """Switch to another tab. Use as a button's on_click."""
    st.session_state.view = view
