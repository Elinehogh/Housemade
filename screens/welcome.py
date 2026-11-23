"""The welcome page before login: what Housemade is, and the Google login button."""

import streamlit as st

from config import TAGLINE

PRIVACY_URL = "https://github.com/Elinehogh/Housemade/blob/main/PRIVACY.md"

FEATURES = [
    ("🧹", "Chores", "Who does what and by when. Tick chores off, earn points and win the week."),
    ("🛒", "Shopping and costs", "One shared list, costs split fairly, and a clear view of who owes whom."),
    ("🫙", "Shared fund", "Collect pant money, save towards a goal and pick things to do together."),
]


def show() -> None:
    st.markdown(f"### {TAGLINE}")
    st.write("Housemade keeps your flat organised, so nobody has to nag and nobody forgets who paid.")

    for column, (icon, title, text) in zip(st.columns(3), FEATURES):
        with column.container(border=True, height="stretch"):
            st.markdown(f"## {icon}")
            st.markdown(f"**{title}**")
            st.caption(text)

    st.write("")
    st.button("Log in with Google", type="primary", icon=":material/login:", on_click=st.login)
    st.caption(f"We only get your name and email from Google. [Privacy policy]({PRIVACY_URL})")
