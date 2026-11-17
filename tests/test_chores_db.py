"""Database tests for chores. Each test gets a fresh in-memory SQLite database, never the real one."""

from datetime import date, datetime

import pytest

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
