"""Database tests for the fund. Each test gets a fresh in-memory SQLite database, never the real one."""

import csv
import io
from datetime import date, datetime

import pytest

import db
from logic import fund_csv

MONDAY = datetime(2026, 11, 16, 12, 0)
TUESDAY = datetime(2026, 11, 17, 12, 0)


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
    """Ben is a member of Anna's flat."""
    ben = db.get_or_create_user(engine, "ben@example.com", "Ben")
    db.join_flat(engine, ben, db.get_membership(engine, anna)["invite_code"])
    return ben


@pytest.fixture
def carl(engine):
    """Carl is the admin of another flat."""
    carl = db.get_or_create_user(engine, "carl@example.com", "Carl")
    db.create_flat(engine, carl, "Other flat")
    return carl


# --- Pant in ----------------------------------------------------------------


def test_new_fund_is_empty(engine, anna):
    assert db.fund_balance(engine, anna) == 0
    assert db.fund_history(engine, anna) == []


def test_any_member_can_add_pant(engine, anna, ben):
    db.add_pant(engine, ben, 6.40, now=MONDAY)
    assert db.fund_balance(engine, anna) == 640
    assert db.fund_history(engine, anna) == [{"date": date(2026, 11, 16), "what": "Pant", "who": "Ben", "cents": 640}]


@pytest.mark.parametrize("amount", [0, -3, 1000.01])
def test_invalid_pant_is_not_saved(engine, anna, amount):
    with pytest.raises(ValueError):
        db.add_pant(engine, anna, amount)
    assert db.fund_history(engine, anna) == []


def test_user_without_a_flat_cannot_add_pant(engine):
    loner = db.get_or_create_user(engine, "loner@example.com", "Loner")
    with pytest.raises(ValueError):
        db.add_pant(engine, loner, 5)


# --- Money out --------------------------------------------------------------


def test_admin_can_take_money_out(engine, anna, ben):
    db.add_pant(engine, ben, 30, now=MONDAY)
    db.take_out(engine, anna, " Pizza   night ", 24, now=TUESDAY)
    assert db.fund_balance(engine, ben) == 600
    assert db.fund_history(engine, ben)[0] == {"date": date(2026, 11, 17), "what": "Pizza night", "who": "Anna", "cents": -2400}


def test_admin_can_empty_the_fund_exactly(engine, anna):
    db.add_pant(engine, anna, 5)
    db.take_out(engine, anna, "Snacks", 5)
    assert db.fund_balance(engine, anna) == 0


def test_fund_cannot_go_below_zero(engine, anna):
    db.add_pant(engine, anna, 5)
    with pytest.raises(ValueError):
        db.take_out(engine, anna, "Snacks", 5.01)
    assert db.fund_balance(engine, anna) == 500


def test_member_cannot_take_money_out(engine, anna, ben):
    db.add_pant(engine, anna, 50)
    with pytest.raises(ValueError):
        db.take_out(engine, ben, "Snacks", 5)
    assert db.fund_balance(engine, anna) == 5000


@pytest.mark.parametrize("what, amount", [("", 5), ("a" * 41, 5), ("Snacks", 0)])
def test_invalid_withdrawal_is_not_saved(engine, anna, what, amount):
    db.add_pant(engine, anna, 50)
    with pytest.raises(ValueError):
        db.take_out(engine, anna, what, amount)
    assert db.fund_balance(engine, anna) == 5000


# --- Only your own flat -----------------------------------------------------


def test_other_flats_do_not_see_your_fund(engine, anna, carl):
    db.add_pant(engine, anna, 10)
    assert db.fund_balance(engine, carl) == 0
    assert db.fund_history(engine, carl) == []


def test_admin_of_another_flat_cannot_spend_your_money(engine, anna, carl):
    db.add_pant(engine, anna, 10)
    with pytest.raises(ValueError):
        db.take_out(engine, carl, "Snacks", 5)
    assert db.fund_balance(engine, anna) == 1000


# --- History and CSV --------------------------------------------------------


def test_history_is_newest_first(engine, anna, ben):
    db.add_pant(engine, ben, 3, now=MONDAY)
    db.add_pant(engine, anna, 4, now=TUESDAY)
    assert [entry["who"] for entry in db.fund_history(engine, anna)] == ["Anna", "Ben"]


def test_balance_equals_the_history_and_the_csv(engine, anna, ben):
    for amount in (0.10, 0.20, 6.40, 3.33):
        db.add_pant(engine, ben, amount)
    db.take_out(engine, anna, "Pizza night", 9.99)
    history = db.fund_history(engine, anna)
    balance = db.fund_balance(engine, anna)
    assert balance == sum(entry["cents"] for entry in history) == 4
    rows = list(csv.DictReader(io.StringIO(fund_csv(history))))
    assert round(sum(float(row["amount_eur"]) for row in rows) * 100) == balance


# --- Goal -------------------------------------------------------------------


def test_flat_has_no_goal_at_first(engine, anna):
    assert db.get_fund_goal(engine, anna) is None


def test_admin_can_set_and_replace_the_goal(engine, anna, ben):
    db.set_fund_goal(engine, anna, "Trip to Sintra", 80)
    db.set_fund_goal(engine, anna, "Trip to Porto", 150)
    assert db.get_fund_goal(engine, ben) == {"name": "Trip to Porto", "cents": 15000}


def test_member_cannot_set_the_goal(engine, anna, ben):
    with pytest.raises(ValueError):
        db.set_fund_goal(engine, ben, "Trip to Sintra", 80)
    assert db.get_fund_goal(engine, anna) is None


def test_goal_with_invalid_amount_is_rejected(engine, anna):
    with pytest.raises(ValueError):
        db.set_fund_goal(engine, anna, "Trip", 0)


def test_other_flats_do_not_see_your_goal(engine, anna, carl):
    db.set_fund_goal(engine, anna, "Trip to Sintra", 80)
    assert db.get_fund_goal(engine, carl) is None
