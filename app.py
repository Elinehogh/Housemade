"""The screens. Start reading here."""

import streamlit as st

import db
from config import APP_NAME, LOCAL_DATABASE_URL, TAGLINE
from logic import display_name
from screens import activities, chores, demo_data, fund, shopping

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


def login_is_set_up() -> bool:
    """True when the Google login keys are in the secrets (not the placeholders)."""
    try:
        return not st.secrets["auth"]["client_id"].startswith(("PASTE", "YOUR"))
    except (KeyError, FileNotFoundError):
        return False


st.title(f"🏠 {APP_NAME}")
st.caption(TAGLINE)

if login_is_set_up():
    engine = get_engine()
    if engine.dialect.name == "sqlite":
        st.warning("Using a local test database: data is not shared and may be lost. "
                   "Set DATABASE_URL in the secrets to use the real database.")

    # --- Login ---------------------------------------------------------------

    if not st.user.get("is_logged_in"):
        st.write("Keep track of chores, shopping and the shared fund in your flat.")
        st.button("Log in with Google", type="primary", on_click=st.login)
        st.stop()

    user_id = db.get_or_create_user(engine, st.user.email, display_name(st.user.get("name"), st.user.email))

    with st.sidebar:
        st.write(f"Logged in as **{st.user.get('name') or st.user.email}**")
        st.button("Log out", on_click=st.logout)

    # --- Create or join a flat -----------------------------------------------

    membership = db.get_membership(engine, user_id)

    if membership is None:
        st.subheader("Get started")
        create_tab, join_tab = st.tabs(["Create a flat", "Join a flat"])

        with create_tab:
            with st.form("create_flat"):
                flat_name = st.text_input("Name of your flat", placeholder="Rua Augusta 12")
                if st.form_submit_button("Create flat"):
                    try:
                        db.create_flat(engine, user_id, flat_name)
                        st.rerun()
                    except ValueError as error:
                        st.error(str(error))

        with join_tab:
            with st.form("join_flat"):
                code = st.text_input("Invite code", placeholder="K7QX2M")
                if st.form_submit_button("Join flat"):
                    try:
                        db.join_flat(engine, user_id, code)
                        st.rerun()
                    except ValueError as error:
                        st.error(str(error))
        st.stop()

    flat_name = membership["flat_name"]
    members = db.list_members(engine, user_id)
    invite_code = membership["invite_code"] if membership["role"] == "admin" else None
else:
    st.info("**Preview with sample data.** Login is not set up yet, and nothing you do here is saved.")
    flat_name = "Demo flat"
    engine = user_id = None
    members = [{"name": name, "role": "admin" if name == "You" else "member"} for name in demo_data.MEMBERS]
    invite_code = "K7QX2M"

# --- The flat ----------------------------------------------------------------

demo_data.init()

st.header(flat_name)
home_tab, chores_tab, shopping_tab, fund_tab, activities_tab = st.tabs(
    ["🏠 Flat", "🧹 Chores", "🛒 Shopping", "🫙 Fund", "🎉 Activities"]
)

with home_tab:
    if invite_code:
        st.info(f"Invite your flatmates with the code **{invite_code}**")
    st.write("**Members**")
    for member in members:
        badge = " (admin)" if member["role"] == "admin" else ""
        st.write(f"- {member['name']}{badge}")

with chores_tab:
    chores.show(engine, user_id)
with shopping_tab:
    shopping.show(engine, user_id)
with fund_tab:
    fund.show()
with activities_tab:
    activities.show()
