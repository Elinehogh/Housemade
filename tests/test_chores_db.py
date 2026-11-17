"""Database tests for chores. Each test gets a fresh in-memory SQLite database, never the real one."""

from datetime import date, datetime

import pytest
from sqlalchemy import inspect, text

import db

THURSDAY = date(2026, 11, 19)
THIS_WEEK = datetime(2026, 11, 17, 10, 0)  # Tuesday
LAST_WEEK = datetime(2026, 11, 15, 23, 59)  # Sunday before


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
    code = db.create_flat(engine, anna, "Rua Augusta 12")
    db.join_flat(engine, ben, code)
    return ben


@pytest.fixture
def carl(engine):
    """Carl lives in another flat."""
    carl = db.get_or_create_user(engine, "carl@example.com", "Carl")
    db.create_flat(engine, carl, "Other flat")
    return carl


# --- Adding -----------------------------------------------------------------


def test_member_can_add_a_chore_for_a_flatmate(engine, anna, ben):
    db.add_chore(engine, anna, " Dishes ", 2, ben)
    chores = db.list_chores(engine, ben)
    assert [(c["name"], c["points"], c["who"], c["done"]) for c in chores] == [("Dishes", 2, "Ben", False)]


def test_flatmates_see_the_same_chores(engine, anna, ben):
    db.add_chore(engine, anna, "Dishes", 2, ben)
    assert db.list_chores(engine, anna) == db.list_chores(engine, ben)


def test_chore_cannot_be_given_to_someone_in_another_flat(engine, anna, ben, carl):
    with pytest.raises(ValueError):
        db.add_chore(engine, anna, "Dishes", 2, carl)


def test_user_without_a_flat_cannot_add_a_chore(engine, anna):
    with pytest.raises(ValueError):
        db.add_chore(engine, anna, "Dishes", 2, anna)


@pytest.mark.parametrize("name, points", [("", 2), ("Dishes", 0), ("Dishes", 11)])
def test_invalid_chore_is_not_saved(engine, anna, ben, name, points):
    with pytest.raises(ValueError):
        db.add_chore(engine, anna, name, points, ben)
    assert db.list_chores(engine, anna) == []


def test_other_flats_do_not_see_your_chores(engine, anna, ben, carl):
    db.add_chore(engine, anna, "Dishes", 2, ben)
    assert db.list_chores(engine, carl) == []


# --- Ticking off ------------------------------------------------------------


def test_person_given_the_chore_can_tick_it_off(engine, anna, ben):
    chore = db.add_chore(engine, anna, "Dishes", 2, ben)
    db.tick_off_chore(engine, ben, chore)
    assert db.list_chores(engine, anna)[0]["done"] is True


def test_someone_else_cannot_tick_off_the_chore(engine, anna, ben):
    chore = db.add_chore(engine, anna, "Dishes", 2, ben)
    with pytest.raises(ValueError):
        db.tick_off_chore(engine, anna, chore)
    assert db.list_chores(engine, anna)[0]["done"] is False


def test_chore_cannot_be_ticked_off_twice(engine, anna, ben):
    chore = db.add_chore(engine, anna, "Dishes", 2, ben)
    db.tick_off_chore(engine, ben, chore, now=THIS_WEEK)
    with pytest.raises(ValueError):
        db.tick_off_chore(engine, ben, chore, now=THIS_WEEK)
    assert db.chores_leaderboard(engine, ben, THURSDAY) == [("Ben", 2), ("Anna", 0)]


def test_chore_from_another_flat_cannot_be_ticked_off(engine, anna, ben, carl):
    chore = db.add_chore(engine, anna, "Dishes", 2, ben)
    with pytest.raises(ValueError):
        db.tick_off_chore(engine, carl, chore)


def test_unknown_chore_cannot_be_ticked_off(engine, anna, ben):
    with pytest.raises(ValueError):
        db.tick_off_chore(engine, ben, 999)


def test_open_chores_are_listed_before_done_ones(engine, anna, ben):
    first = db.add_chore(engine, anna, "Dishes", 2, ben)
    db.add_chore(engine, anna, "Trash", 1, ben)
    db.tick_off_chore(engine, ben, first)
    assert [c["name"] for c in db.list_chores(engine, ben)] == ["Trash", "Dishes"]


# --- Leaderboard ------------------------------------------------------------


def test_leaderboard_counts_only_this_week(engine, anna, ben):
    old = db.add_chore(engine, anna, "Old dishes", 5, ben)
    new = db.add_chore(engine, anna, "Trash", 1, anna)
    db.tick_off_chore(engine, ben, old, now=LAST_WEEK)
    db.tick_off_chore(engine, anna, new, now=THIS_WEEK)
    assert db.chores_leaderboard(engine, anna, THURSDAY) == [("Anna", 1), ("Ben", 0)]


def test_open_chores_give_no_points(engine, anna, ben):
    db.add_chore(engine, anna, "Dishes", 2, ben)
    assert db.chores_leaderboard(engine, anna, THURSDAY) == [("Anna", 0), ("Ben", 0)]


def test_leaderboard_shows_only_your_own_flat(engine, anna, ben, carl):
    assert db.chores_leaderboard(engine, carl, THURSDAY) == [("Carl", 0)]


# --- Deadlines and logging done chores -----------------------------------------------


def test_chore_can_have_a_deadline(engine, anna, ben):
    db.add_chore(engine, anna, "Vacuum", 3, ben, due_on=date(2026, 11, 20), today=THURSDAY)
    assert db.list_chores(engine, ben)[0]["due_on"] == date(2026, 11, 20)


def test_chore_can_have_no_deadline(engine, anna, ben):
    db.add_chore(engine, anna, "Vacuum", 3, ben)
    assert db.list_chores(engine, ben)[0]["due_on"] is None


def test_chore_with_a_deadline_in_the_past_is_not_saved(engine, anna, ben):
    with pytest.raises(ValueError):
        db.add_chore(engine, anna, "Vacuum", 3, ben, due_on=date(2026, 11, 18), today=THURSDAY)
    assert db.list_chores(engine, anna) == []


def test_open_chores_are_listed_by_deadline_and_without_deadline_last(engine, anna, ben):
    db.add_chore(engine, anna, "No deadline", 1, ben)
    db.add_chore(engine, anna, "Later", 1, ben, due_on=date(2026, 11, 25), today=THURSDAY)
    db.add_chore(engine, anna, "Soon", 1, ben, due_on=date(2026, 11, 20), today=THURSDAY)
    done = db.add_chore(engine, anna, "Done", 1, anna, due_on=date(2026, 11, 19), today=THURSDAY)
    db.tick_off_chore(engine, anna, done)
    assert [c["name"] for c in db.list_chores(engine, anna)] == ["Soon", "Later", "No deadline", "Done"]


def test_logged_chore_is_done_and_yours(engine, anna, ben):
    db.log_chore(engine, ben, "Take out the trash", 1, now=THIS_WEEK)
    [chore] = db.list_chores(engine, anna)
    assert chore["done"] and chore["who"] == "Ben" and chore["done_at"] == THIS_WEEK


def test_logged_chore_counts_for_the_leaderboard(engine, anna, ben):
    db.log_chore(engine, ben, "Take out the trash", 1, now=THIS_WEEK)
    assert db.chores_leaderboard(engine, anna, today=THURSDAY) == [("Ben", 1), ("Anna", 0)]


@pytest.mark.parametrize("name, points", [("", 1), ("Trash", 0), ("Trash", 11)])
def test_invalid_logged_chore_is_not_saved(engine, anna, ben, name, points):
    with pytest.raises(ValueError):
        db.log_chore(engine, anna, name, points)
    assert db.list_chores(engine, anna) == []


def test_user_without_a_flat_cannot_log_a_chore(engine, anna):
    with pytest.raises(ValueError):
        db.log_chore(engine, anna, "Trash", 1)


# --- Adding new columns to an existing database ------------------------------


def test_missing_deadline_column_is_added_without_losing_chores():
    """A database made before deadlines existed gets the new column, and old chores are kept."""
    engine = db.engine_from_url("sqlite://")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE chores (id INTEGER PRIMARY KEY, flat_id INTEGER, name VARCHAR(40), "
                          "points INTEGER, assigned_to INTEGER, done_at DATETIME)"))
        conn.execute(text("INSERT INTO chores (flat_id, name, points, assigned_to) VALUES (1, 'Old chore', 2, 1)"))
    db.create_tables(engine)
    assert "due_on" in {column["name"] for column in inspect(engine).get_columns("chores")}
    with engine.connect() as conn:
        assert conn.execute(text("SELECT name, due_on FROM chores")).all() == [("Old chore", None)]


def test_running_create_tables_twice_changes_nothing(engine):
    db.create_tables(engine)
    assert "due_on" in {column["name"] for column in inspect(engine).get_columns("chores")}


def test_schema_changes_when_a_column_is_added():
    """app.py uses db.schema() to know when to add new tables and columns without a reboot."""
    assert ("chores", ("id", "flat_id", "name", "points", "assigned_to", "done_at", "due_on")) in db.schema()
