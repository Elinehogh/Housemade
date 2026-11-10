"""The screens. Start reading here."""

import streamlit as st

from config import APP_NAME, TAGLINE
from logic import clean_member_name

st.set_page_config(page_title=APP_NAME, page_icon="🏠")

st.title(f"🏠 {APP_NAME}")
st.caption(TAGLINE)

st.write("Hello, flat! The app is up and running. Features are coming soon.")

raw_name = st.text_input("What's your name?")
if raw_name:
    try:
        st.success(f"Welcome, {clean_member_name(raw_name)}!")
    except ValueError as error:
        st.error(str(error))
