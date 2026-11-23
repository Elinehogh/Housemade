"""Tests for the text on the Today tiles (specs/design.md)."""

import pytest

import db
from logic import money_detail, money_summary, to_buy_text, weather_headline

# --- Weather headline ------------------------------------------------------------


@pytest.mark.parametrize("kind, word", [
    ("sunny", "Sunny"), ("cloudy", "Cloudy"), ("foggy", "Foggy"),
    ("rainy", "Rainy"), ("snowy", "Snowy"), ("stormy", "Stormy"),
])
def test_headline_names_the_weather_and_the_city(kind, word):
    assert weather_headline(kind, "Lisbon") == f"{word} today in Lisbon"


def test_unknown_weather_is_rejected():
    with pytest.raises(ValueError):
        weather_headline("raining frogs", "Lisbon")


# --- Money tile ------------------------------------------------------------------


def test_negative_balance_means_you_owe():
    assert money_summary(-720) == ("You owe", "€7.20")


def test_positive_balance_means_you_get_back():
    assert money_summary(1250) == ("You get back", "€12.50")


def test_zero_balance_is_even():
    assert money_summary(0) == ("All even", "€0.00")


def test_detail_lists_who_to_pay():
    assert money_detail([("Ana", 400), ("Tom", 320)], []) == ["€4.00 to Ana", "€3.20 to Tom"]


def test_detail_lists_who_pays_you():
    assert money_detail([], [("Sara", 1440)]) == ["€14.40 from Sara"]


def test_detail_is_empty_when_even():
    assert money_detail([], []) == []


# --- Shopping tile ---------------------------------------------------------------


def test_empty_list_says_nothing_to_buy():
    assert to_buy_text([]) == "Nothing to buy"


def test_one_item():
    assert to_buy_text(["Milk"]) == "Milk"


def test_two_items_are_both_shown():
    assert to_buy_text(["Toilet paper", "Dish soap"]) == "Toilet paper, Dish soap"


def test_more_items_are_counted():
    assert to_buy_text(["Toilet paper", "Dish soap", "Milk", "Salt"]) == "Toilet paper, Dish soap and 2 more"


# --- Who the member pays ----------------------------------------------------------


@pytest.fixture
def engine():
    engine = db.engine_from_url("sqlite://")
    db.create_tables(engine)
    return engine


def flat(engine, *names):
    ids = [db.get_or_create_user(engine, f"{i}@example.com", name) for i, name in enumerate(names)]
    code = db.create_flat(engine, ids[0], "Rua Augusta 12")
    for member in ids[1:]:
        db.join_flat(engine, member, code)
    return ids


def test_member_who_owes_sees_who_to_pay(engine):
    anna, ben = flat(engine, "Anna", "Ben")
    db.add_expense(engine, anna, 10, "Soap")
    money = db.money_overview(engine, ben)
    assert money["mine_to_pay"] == [("Anna", 500)]
    assert money["mine_to_get"] == []


def test_member_who_paid_sees_who_pays_them(engine):
    anna, ben = flat(engine, "Anna", "Ben")
    db.add_expense(engine, anna, 10, "Soap")
    money = db.money_overview(engine, anna)
    assert money["mine_to_get"] == [("Ben", 500)]
    assert money["mine_to_pay"] == []


def test_flatmates_with_the_same_name_are_kept_apart(engine):
    payer, first_ana, second_ana = flat(engine, "Tom", "Ana", "Ana")
    db.add_expense(engine, first_ana, 30, "Soap")
    assert db.money_overview(engine, first_ana)["mine_to_pay"] == []
    assert len(db.money_overview(engine, second_ana)["mine_to_pay"]) == 1


def test_nothing_to_pay_without_costs(engine):
    anna, _ = flat(engine, "Anna", "Ben")
    money = db.money_overview(engine, anna)
    assert (money["mine_to_pay"], money["mine_to_get"]) == ([], [])
