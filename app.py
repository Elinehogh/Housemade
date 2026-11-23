"""The screens. Start reading here."""

import streamlit as st

import db
from config import APP_NAME, LOCAL_DATABASE_URL
from logic import avatar_label, display_name
from screens import activities, avatar, chores, demo_data, fund, home, house_rules, shopping, sky, welcome

st.set_page_config(page_title=APP_NAME, page_icon="🏠")
sky.apply()


@st.cache_resource
def get_engine():
    """Connect once per app process: Supabase if the secret is set, else a local file."""
    try:
        url = st.secrets["DATABASE_URL"]
    except (KeyError, FileNotFoundError):
        url = LOCAL_DATABASE_URL
    return db.engine_from_url(url)


@st.cache_resource
def make_tables(_engine, schema: tuple) -> None:
    """Create missing tables and columns once per version of the tables.

    Streamlit Cloud keeps the app running when new code is merged, so get_engine() is not run again.
    Because every table and column name is part of the cache key, a new table or column is added right away.
    """
    db.create_tables(_engine)


def known_user_id(engine, email: str, name: str) -> int:
    """The member's user id. It never changes, so it is looked up only once per visit (specs/speed.md)."""
    saved = st.session_state.get("known_user")
    if saved is None or saved["email"] != email:
        saved = {"email": email, "id": db.get_or_create_user(engine, email, name)}
        st.session_state.known_user = saved
    return saved["id"]


def login_is_set_up() -> bool:
    """True when the Google login keys are in the secrets (not the placeholders)."""
    try:
        return not st.secrets["auth"]["client_id"].startswith(("PASTE", "YOUR"))
    except (KeyError, FileNotFoundError):
        return False


st.title(APP_NAME)

if login_is_set_up():
    engine = get_engine()
    make_tables(engine, db.schema())
    if engine.dialect.name == "sqlite":
        st.warning("Using a local test database: data is not shared and may be lost. "
                   "Set DATABASE_URL in the secrets to use the real database.")

    # --- Login ---------------------------------------------------------------

    if not st.user.get("is_logged_in"):
        welcome.show()
        st.stop()

    me = display_name(st.user.get("name"), st.user.email)
    user_id = known_user_id(engine, st.user.email, me)
    context = db.member_context(engine, user_id)

    # --- Avatar: picked once, right after the first login ----------------------

    my_avatar = context["avatar"]
    if my_avatar is None:
        st.subheader(f"👋 Hi {me}! Pick your avatar")
        st.caption("Your flatmates will see it next to your name. You can change it later.")
        avatar.picker(engine, user_id, key="first_avatar")
        st.stop()

    with st.sidebar:
        st.markdown(f"## {avatar_label(*my_avatar)}")
        st.write(f"Logged in as **{st.user.get('name') or st.user.email}**")
        with st.popover("Change avatar", icon=":material/face:"):
            avatar.picker(engine, user_id, key="sidebar_avatar", avatar=my_avatar)
        st.button("Log out", icon=":material/logout:", on_click=st.logout)

    # --- Create or join a flat -----------------------------------------------

    membership = context["membership"]

    if membership is None:
        st.subheader("👋 Welcome! Let's set up your flat")
        st.caption("Create a new flat and invite your flatmates, or join one with the code you got.")
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
    st.sidebar.write(f"🏠 {flat_name}")
    invite_code = membership["invite_code"] if membership["role"] == "admin" else None
else:
    st.info("**Preview with sample data.** Login is not set up yet, and nothing you do here is saved.")
    flat_name = "Demo flat"
    engine = user_id = my_avatar = None
    me = "You"
    invite_code = "K7QX2M"

# --- The flat ----------------------------------------------------------------

demo_data.init()

st.caption(f"Your flat: **{flat_name}**")
# Only the open tab is drawn. The Today tab can open another one through st.session_state.view.
today_tab, chores_tab, shopping_tab, fund_tab, activities_tab, rules_tab = st.tabs(
    sky.VIEWS, key="view", on_change="rerun"
)

with today_tab:
    if today_tab.open:
        home.show(engine, user_id, invite_code, me, my_avatar)
with chores_tab:
    if chores_tab.open:
        chores.show(engine, user_id)
with shopping_tab:
    if shopping_tab.open:
        shopping.show(engine, user_id)
with fund_tab:
    if fund_tab.open:
        fund.show(engine, user_id)
with activities_tab:
    if activities_tab.open:
        activities.show(engine, user_id)
with rules_tab:
    if rules_tab.open:
        house_rules.show(engine, user_id)
