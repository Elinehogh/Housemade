"""Tests for avatars (specs/design.md): the rules in logic.py and saving them in db.py."""

import pytest
from sqlalchemy import inspect, text

import db
from logic import AVATAR_COLORS, AVATAR_EMOJIS, DEFAULT_AVATAR, avatar_label, check_avatar


# --- Rules -------------------------------------------------------------------


def test_lists_have_16_emojis_and_7_colours_without_repeats():
    assert len(set(AVATAR_EMOJIS)) == len(AVATAR_EMOJIS) == 16
    assert len(set(AVATAR_COLORS)) == len(AVATAR_COLORS) == 7


def test_avatar_from_the_lists_is_accepted():
    assert check_avatar(AVATAR_EMOJIS[0], AVATAR_COLORS[0]) == (AVATAR_EMOJIS[0], AVATAR_COLORS[0])


@pytest.mark.parametrize("emoji, color", [("💩", "blue"), ("🦊", "pink"), ("", "blue"), ("🦊", ""), ("<b>", "blue")])
def test_avatar_not_from_the_lists_is_rejected(emoji, color):
    with pytest.raises(ValueError):
        check_avatar(emoji, color)


def test_avatar_label_shows_emoji_on_colour():
    assert avatar_label("🦊", "orange") == ":orange-background[🦊]"


def test_missing_avatar_gets_the_default():
    assert avatar_label(None, None) == avatar_label(*DEFAULT_AVATAR)


# --- Saving ------------------------------------------------------------------


@pytest.fixture
def engine():
    engine = db.engine_from_url("sqlite://")
    db.create_tables(engine)
    return engine


@pytest.fixture
def anna(engine):
    return db.get_or_create_user(engine, "anna@example.com", "Anna")


@pytest.fixture
def ben(engine, anna):
    """Ben lives with Anna."""
    ben = db.get_or_create_user(engine, "ben@example.com", "Ben")
    db.join_flat(engine, ben, db.create_flat(engine, anna, "Rua Augusta 12"))
    return ben


@pytest.fixture
def carl(engine):
    """Carl lives in another flat."""
    carl = db.get_or_create_user(engine, "carl@example.com", "Carl")
    db.create_flat(engine, carl, "Other flat")
    return carl


def test_new_user_has_no_avatar(engine, anna):
    assert db.get_avatar(engine, anna) is None


def test_avatar_is_saved_and_can_be_changed(engine, anna):
    db.set_avatar(engine, anna, "🦊", "orange")
    db.set_avatar(engine, anna, "🐼", "green")
    assert db.get_avatar(engine, anna) == ("🐼", "green")


def test_avatar_can_be_picked_before_joining_a_flat(engine, anna):
    db.set_avatar(engine, anna, "🦊", "orange")
    assert db.get_avatar(engine, anna) == ("🦊", "orange")


def test_invalid_avatar_is_not_saved(engine, anna):
    with pytest.raises(ValueError):
        db.set_avatar(engine, anna, "💩", "orange")
    assert db.get_avatar(engine, anna) is None


def test_flatmates_see_each_others_avatars(engine, anna, ben):
    db.set_avatar(engine, anna, "🦊", "orange")
    assert db.flat_avatars(engine, ben) == {"Anna": ("🦊", "orange"), "Ben": (None, None)}


def test_other_flats_avatars_are_not_shown(engine, anna, ben, carl):
    db.set_avatar(engine, carl, "🐸", "green")
    assert "Carl" not in db.flat_avatars(engine, anna)


def test_avatar_columns_are_added_to_an_existing_database():
    engine = db.engine_from_url("sqlite://")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR(254), name VARCHAR(30))"))
        conn.execute(text("INSERT INTO users (email, name) VALUES ('old@example.com', 'Old')"))
    db.create_tables(engine)
    columns = {column["name"] for column in inspect(engine).get_columns("users")}
    assert {"avatar_emoji", "avatar_color"} <= columns
    with engine.connect() as conn:
        assert conn.execute(text("SELECT name, avatar_emoji FROM users")).all() == [("Old", None)]
