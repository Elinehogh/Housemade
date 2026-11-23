"""Tests for loading the Today tab in one database visit (specs/speed.md)."""

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import event

import db

TODAY = date(2026, 11, 25)  # a Wednesday
THIS_WEEK = datetime(2026, 11, 24, 12, 0)
LAST_WEEK = datetime(2026, 11, 20, 12, 0)


@pytest.fixture
def engine():
    engine = db.engine_from_url("sqlite://")
    db.create_tables(engine)
    return engine


@pytest.fixture
def anna(engine):
    """Anna is the admin of her flat."""
    anna = db.get_or_create_user(engine, "anna@example.com", "Anna")
    db.create_flat(engine, anna, "Rua Augusta 12")
    return anna


@pytest.fixture
def ben(engine, anna):
    ben = db.get_or_create_user(engine, "ben@example.com", "Ben")
    db.join_flat(engine, ben, db.get_membership(engine, anna)["invite_code"])
    return ben


@pytest.fixture
def carl(engine):
    """Carl is the admin of another flat."""
    carl = db.get_or_create_user(engine, "carl@example.com", "Carl")
    db.create_flat(engine, carl, "Other flat")
    return carl


def fill(engine, anna, ben, extra=0):
    """Give the flat some of everything. extra adds more rows, to check the query count does not grow."""
    db.set_avatar(engine, ben, "🐼", "green")
    done = db.add_chore(engine, anna, "Dishes", 3, ben)
    db.tick_off_chore(engine, ben, done, now=THIS_WEEK)
    old = db.add_chore(engine, anna, "Old chore", 5, ben)
    db.tick_off_chore(engine, ben, old, now=LAST_WEEK)
    db.add_chore(engine, anna, "Vacuum", 2, ben, due_on=TODAY + timedelta(days=1))
    db.add_expense(engine, anna, 20.01, "Soap")
    db.add_expense(engine, ben, 5, "Milk")
    db.confirm_payment(engine, anna, ben, 1)
    db.add_pant(engine, anna, 12.5)
    db.set_fund_goal(engine, anna, "Sintra", 50)
    db.add_item(engine, anna, "Coffee")
    bought = db.add_item(engine, ben, "Salt")
    db.mark_bought(engine, ben, bought)
    picnic = db.add_activity(engine, anna, "Picnic", 15, TODAY, today=TODAY)
    db.add_activity(engine, ben, "Beach", 0, TODAY, today=TODAY)
    db.vote_for_activity(engine, ben, picnic, today=TODAY)
    db.vote_for_activity(engine, anna, picnic, today=TODAY)
    for n in range(extra):
        db.add_chore(engine, anna, f"Chore {n}", 1, ben)
        db.add_item(engine, anna, f"Item {n}")
        db.add_expense(engine, anna, 1, f"Cost {n}")
        activity = db.add_activity(engine, anna, f"Plan {n}", 1, TODAY, today=TODAY)
        db.vote_for_activity(engine, ben, activity, today=TODAY + timedelta(days=n + 1))


def count_trips(engine, action):
    counts = {"queries": 0, "connections": 0}

    def on_query(*_args):
        counts["queries"] += 1

    def on_connection(*_args):
        counts["connections"] += 1

    event.listen(engine, "before_cursor_execute", on_query)
    event.listen(engine, "checkout", on_connection)
    try:
        action()
    finally:
        event.remove(engine, "before_cursor_execute", on_query)
        event.remove(engine, "checkout", on_connection)
    return counts


# --- The same data as the separate functions -------------------------------------


@pytest.mark.parametrize("who", ["anna", "ben"])
def test_overview_matches_the_separate_functions(engine, anna, ben, who):
    fill(engine, anna, ben)
    user = {"anna": anna, "ben": ben}[who]
    data = db.today_overview(engine, user, TODAY)
    money = db.money_overview(engine, user)

    assert data["chores"] == db.list_chores(engine, user)
    assert data["items"] == db.list_items(engine, user)
    assert data["fund"] == db.fund_balance(engine, user)
    assert data["goal"] == db.get_fund_goal(engine, user)
    assert data["activities"] == db.list_activities(engine, user)
    assert data["leaderboard"] == db.chores_leaderboard(engine, user, TODAY)
    assert data["avatars"] == db.flat_avatars(engine, user)
    assert [(m["name"], m["role"]) for m in data["members"]] == [
        (m["name"], m["role"]) for m in db.list_members(engine, user)
    ]
    assert data["my_name"] == db.flat_members(engine, user)[user]
    assert data["money"]["mine"] == money["mine"]
    assert data["money"]["mine_to_pay"] == money["mine_to_pay"]
    assert data["money"]["mine_to_get"] == money["mine_to_get"]


def test_points_from_last_week_do_not_count(engine, anna, ben):
    fill(engine, anna, ben)
    assert dict(db.today_overview(engine, ben, TODAY)["leaderboard"])["Ben"] == 3


def test_empty_flat_has_empty_values(engine, anna):
    data = db.today_overview(engine, anna, TODAY)
    assert (data["chores"], data["items"], data["activities"]) == ([], [], [])
    assert (data["fund"], data["goal"]) == (0, None)
    assert data["money"] == {"mine": 0, "mine_to_pay": [], "mine_to_get": []}
    assert data["leaderboard"] == [("Anna", 0)]


# --- Few trips to the database ---------------------------------------------------


def test_overview_uses_one_connection_and_at_most_seven_queries(engine, anna, ben):
    fill(engine, anna, ben)
    trips = count_trips(engine, lambda: db.today_overview(engine, ben, TODAY))
    assert trips["connections"] == 1
    assert trips["queries"] <= 7


def test_trips_do_not_grow_with_more_data(engine, anna, ben):
    fill(engine, anna, ben)
    small = count_trips(engine, lambda: db.today_overview(engine, ben, TODAY))
    for n in range(10):
        db.add_chore(engine, anna, f"More {n}", 1, ben)
        db.add_item(engine, anna, f"More {n}")
        db.add_activity(engine, anna, f"More {n}", 1, TODAY, today=TODAY)
    assert count_trips(engine, lambda: db.today_overview(engine, ben, TODAY)) == small


def test_member_context_uses_one_query(engine, anna):
    trips = count_trips(engine, lambda: db.member_context(engine, anna))
    assert trips == {"queries": 1, "connections": 1}


def test_a_click_on_today_takes_fewer_than_ten_trips(engine, anna, ben):
    fill(engine, anna, ben)

    def click():
        db.member_context(engine, ben)
        db.today_overview(engine, ben, TODAY)

    trips = count_trips(engine, click)
    assert trips["queries"] + trips["connections"] < 10


# --- Only your own flat ----------------------------------------------------------


def test_overview_never_includes_another_flat(engine, anna, ben, carl):
    fill(engine, anna, ben)
    data = db.today_overview(engine, carl, TODAY)
    assert (data["chores"], data["items"], data["activities"]) == ([], [], [])
    assert (data["fund"], data["goal"]) == (0, None)
    assert [member["name"] for member in data["members"]] == ["Carl"]
    assert data["leaderboard"] == [("Carl", 0)]


def test_user_without_a_flat_is_rejected(engine):
    loner = db.get_or_create_user(engine, "loner@example.com", "Loner")
    with pytest.raises(ValueError):
        db.today_overview(engine, loner, TODAY)


# --- The top of every page -------------------------------------------------------


def test_context_of_a_new_user(engine):
    loner = db.get_or_create_user(engine, "loner@example.com", "Loner")
    assert db.member_context(engine, loner) == {"avatar": None, "membership": None}


def test_context_with_avatar_but_no_flat(engine):
    loner = db.get_or_create_user(engine, "loner@example.com", "Loner")
    db.set_avatar(engine, loner, "🦊", "orange")
    assert db.member_context(engine, loner) == {"avatar": ("🦊", "orange"), "membership": None}


@pytest.mark.parametrize("who", ["anna", "ben"])
def test_context_matches_the_separate_functions(engine, anna, ben, who):
    user = {"anna": anna, "ben": ben}[who]
    db.set_avatar(engine, user, "🐼", "green")
    assert db.member_context(engine, user) == {
        "avatar": db.get_avatar(engine, user),
        "membership": db.get_membership(engine, user),
    }
