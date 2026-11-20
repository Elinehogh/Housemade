"""Database tests for shopping. Each test gets a fresh in-memory SQLite database, never the real one."""

from datetime import datetime

import pytest

import db

NOW = datetime(2026, 11, 18, 17, 30)


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


# --- Shopping list -----------------------------------------------------------


def test_flatmates_see_the_same_list(engine, anna, ben):
    db.add_item(engine, anna, "  Toilet   paper ")
    assert [item["name"] for item in db.list_items(engine, ben)] == ["Toilet paper"]


def test_user_without_a_flat_cannot_add_an_item(engine, anna):
    with pytest.raises(ValueError):
        db.add_item(engine, anna, "Milk")


@pytest.mark.parametrize("name", ["", "x" * 41])
def test_invalid_item_is_not_saved(engine, anna, ben, name):
    with pytest.raises(ValueError):
        db.add_item(engine, anna, name)
    assert db.list_items(engine, anna) == []


def test_same_item_cannot_be_on_the_list_twice(engine, anna, ben):
    db.add_item(engine, anna, "Dish soap")
    with pytest.raises(ValueError):
        db.add_item(engine, ben, "dish SOAP")
    assert len(db.list_items(engine, anna)) == 1


def test_item_can_be_added_again_once_bought(engine, anna, ben):
    item = db.add_item(engine, anna, "Milk")
    db.mark_bought(engine, ben, item)
    db.add_item(engine, anna, "Milk")
    assert len(db.list_items(engine, anna)) == 2


def test_other_flats_do_not_see_your_list(engine, anna, ben, carl):
    db.add_item(engine, anna, "Milk")
    assert db.list_items(engine, carl) == []


def test_buying_saves_who_and_when(engine, anna, ben):
    item = db.add_item(engine, anna, "Milk")
    db.mark_bought(engine, ben, item, now=NOW)
    [saved] = db.list_items(engine, anna)
    assert saved["bought"] and saved["bought_by"] == "Ben" and saved["bought_at"] == NOW


def test_item_cannot_be_bought_twice(engine, anna, ben):
    item = db.add_item(engine, anna, "Milk")
    db.mark_bought(engine, ben, item)
    with pytest.raises(ValueError):
        db.mark_bought(engine, anna, item)


def test_item_from_another_flat_cannot_be_bought(engine, anna, ben, carl):
    item = db.add_item(engine, anna, "Milk")
    with pytest.raises(ValueError):
        db.mark_bought(engine, carl, item)
    assert not db.list_items(engine, anna)[0]["bought"]


def test_open_items_are_listed_before_bought_ones(engine, anna, ben):
    milk = db.add_item(engine, anna, "Milk")
    db.add_item(engine, anna, "Bread")
    db.mark_bought(engine, anna, milk)
    assert [item["name"] for item in db.list_items(engine, anna)] == ["Bread", "Milk"]


def test_member_can_remove_an_item(engine, anna, ben):
    item = db.add_item(engine, anna, "Milk")
    db.remove_item(engine, ben, item)
    assert db.list_items(engine, anna) == []


def test_item_from_another_flat_cannot_be_removed(engine, anna, ben, carl):
    item = db.add_item(engine, anna, "Milk")
    with pytest.raises(ValueError):
        db.remove_item(engine, carl, item)
    assert len(db.list_items(engine, anna)) == 1


def test_clearing_removes_only_bought_items_of_your_flat(engine, anna, ben, carl):
    milk = db.add_item(engine, anna, "Milk")
    db.add_item(engine, anna, "Bread")
    carls = db.add_item(engine, carl, "Milk")
    db.mark_bought(engine, anna, milk)
    db.mark_bought(engine, carl, carls)
    assert db.clear_bought_items(engine, ben) == 1
    assert [item["name"] for item in db.list_items(engine, anna)] == ["Bread"]
    assert len(db.list_items(engine, carl)) == 1


# --- Costs and payments ------------------------------------------------------


def test_cost_is_split_between_the_flat(engine, anna, ben):
    db.add_expense(engine, anna, 30, "Cleaning stuff")
    assert db.money_overview(engine, ben)["balances"] == [("Anna", 1500), ("Ben", -1500)]


def test_cost_is_saved_for_the_person_who_registers_it(engine, anna, ben):
    db.add_expense(engine, ben, 12.5, "Dish soap", now=NOW)
    [expense] = db.money_overview(engine, anna)["expenses"]
    assert expense == {"who": "Ben", "cents": 1250, "description": "Dish soap", "at": NOW}


@pytest.mark.parametrize("amount, description", [(0, "Soap"), (-5, "Soap"), (1.005, "Soap"), (20000, "Soap"), (5, " ")])
def test_invalid_cost_is_not_saved(engine, anna, ben, amount, description):
    with pytest.raises(ValueError):
        db.add_expense(engine, anna, amount, description)
    assert db.money_overview(engine, anna)["expenses"] == []


def test_user_without_a_flat_cannot_add_a_cost(engine, anna):
    with pytest.raises(ValueError):
        db.add_expense(engine, anna, 10, "Soap")


def test_other_flats_do_not_see_your_costs(engine, anna, ben, carl):
    db.add_expense(engine, anna, 30, "Cleaning stuff")
    overview = db.money_overview(engine, carl)
    assert overview["expenses"] == [] and overview["balances"] == [("Carl", 0)]


def test_settle_up_suggests_who_pays_whom(engine, anna, ben):
    db.add_expense(engine, anna, 30, "Cleaning stuff")
    assert db.money_overview(engine, anna)["settle_up"] == [("Ben", "Anna", 1500)]


def test_receiver_confirms_a_payment_and_the_debt_is_gone(engine, anna, ben):
    db.add_expense(engine, anna, 30, "Cleaning stuff")
    db.confirm_payment(engine, anna, ben, 15)
    overview = db.money_overview(engine, ben)
    assert overview["balances"] == [("Anna", 0), ("Ben", 0)]
    assert overview["settle_up"] == []
    assert overview["payments"][0]["from"] == "Ben" and overview["payments"][0]["to"] == "Anna"


def test_you_cannot_confirm_a_payment_from_yourself(engine, anna, ben):
    db.add_expense(engine, anna, 30, "Cleaning stuff")
    with pytest.raises(ValueError):
        db.confirm_payment(engine, ben, ben, 15)
    assert db.money_overview(engine, anna)["payments"] == []


def test_you_cannot_confirm_a_payment_from_another_flat(engine, anna, ben, carl):
    with pytest.raises(ValueError):
        db.confirm_payment(engine, anna, carl, 15)
    assert db.money_overview(engine, anna)["payments"] == []


@pytest.mark.parametrize("amount", [0, -1, 1.001])
def test_invalid_payment_is_not_saved(engine, anna, ben, amount):
    with pytest.raises(ValueError):
        db.confirm_payment(engine, anna, ben, amount)
    assert db.money_overview(engine, anna)["payments"] == []


def test_overview_includes_your_own_balance(engine, anna, ben):
    db.add_expense(engine, anna, 30, "Cleaning stuff")
    assert db.money_overview(engine, anna)["mine"] == 1500
    assert db.money_overview(engine, ben)["mine"] == -1500
