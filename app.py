"""The screens. Start reading here."""

import streamlit as st

import db
from config import APP_NAME, LOCAL_DATABASE_URL, TAGLINE
from logic import clean_member_name

st.set_page_config(page_title=APP_NAME, page_icon="🏠")


@st.cache_resource
def get_engine():
    """Connect once per app process: Supabase if the secret is set, else a local file."""
    try:
        url = st.secrets["DATABASE_URL"]
    except (KeyError, FileNotFoundError):
        url = LOCAL_DATABASE_URL
    engine = db.engine_from_url(url)
    db.create_tables(engine)
    return engine


engine = get_engine()

st.title(f"🏠 {APP_NAME}")
st.caption(TAGLINE)

st.write("Hello, flat! The app is up and running. Features are coming soon.")

raw_name = st.text_input("What's your name?")
if raw_name:
    try:
        st.success(f"Welcome, {clean_member_name(raw_name)}!")
    except ValueError as error:
        st.error(str(error))

st.caption(f"Database: {engine.dialect.name}")
