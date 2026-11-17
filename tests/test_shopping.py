"""Tests for the shopping rules in logic.py: items, money in cents, splitting and settling up."""

import pytest

from logic import (
    COMMON_ITEMS,
    MAX_AMOUNT_CENTS,
    MAX_DESCRIPTION_LENGTH,
    MAX_ITEM_LENGTH,
    check_payment,
    clean_description,
    clean_item_name,
    euros,
    shopping_balances,
    split_cents,
    settle_up,
    to_cents,
)

ANA, BEN, TOM = 1, 2, 3


# --- Items -------------------------------------------------------------------


def test_item_name_is_tidied():
    assert clean_item_name("  Dish   soap ") == "Dish soap"


@pytest.mark.parametrize("raw", ["", "   "])
def test_empty_item_name_is_rejected(raw):
    with pytest.raises(ValueError):
        clean_item_name(raw)


def test_item_name_at_max_length_is_accepted():
    assert clean_item_name("x" * MAX_ITEM_LENGTH) == "x" * MAX_ITEM_LENGTH


def test_item_name_over_max_length_is_rejected():
    with pytest.raises(ValueError):
        clean_item_name("x" * (MAX_ITEM_LENGTH + 1))


def test_common_items_are_valid_and_unique():
    assert len({item.lower() for item in COMMON_ITEMS}) == len(COMMON_ITEMS)
    for item in COMMON_ITEMS:
        assert clean_item_name(item) == item


def test_description_is_tidied_and_checked():
    assert clean_description(" Cleaning  stuff ") == "Cleaning stuff"
    with pytest.raises(ValueError):
        clean_description(" ")
    with pytest.raises(ValueError):
        clean_description("x" * (MAX_DESCRIPTION_LENGTH + 1))


# --- Money -------------------------------------------------------------------


@pytest.mark.parametrize("raw, cents", [(18.4, 1840), (0.01, 1), (7, 700), ("12.50", 1250), (10000, MAX_AMOUNT_CENTS)])
def test_amount_is_turned_into_cents(raw, cents):
    assert to_cents(raw) == cents


@pytest.mark.parametrize("raw", [0, -5, 10000.01, 1.005, "abc", float("nan"), float("inf")])
def test_invalid_amount_is_rejected(raw):
    with pytest.raises(ValueError):
        to_cents(raw)


def test_cents_are_shown_as_euros():
    assert euros(1840) == "€18.40"
    assert euros(-500) == "-€5.00"
    assert euros(0) == "€0.00"


# --- Splitting ---------------------------------------------------------------


def test_even_split():
    assert split_cents(3000, 3) == [1000, 1000, 1000]


def test_uneven_split_loses_no_cents():
    shares = split_cents(1000, 3)
    assert shares == [334, 333, 333]
    assert sum(shares) == 1000


def test_split_with_fewer_cents_than_people():
    assert split_cents(2, 3) == [1, 1, 0]


def test_split_between_nobody_is_rejected():
    with pytest.raises(ValueError):
        split_cents(1000, 0)


def test_payer_gets_back_what_others_owe():
    balances = shopping_balances([ANA, BEN, TOM], [(ANA, 3000)], [])
    assert balances == {ANA: 2000, BEN: -1000, TOM: -1000}


def test_balances_add_up_to_zero_with_uneven_costs():
    expenses = [(ANA, 1000), (BEN, 1), (TOM, 999), (ANA, 2)]
    assert sum(shopping_balances([ANA, BEN, TOM], expenses, []).values()) == 0


def test_payment_reduces_what_is_owed():
    balances = shopping_balances([ANA, BEN, TOM], [(ANA, 3000)], [(BEN, ANA, 1000)])
    assert balances == {ANA: 1000, BEN: 0, TOM: -1000}


def test_no_costs_means_everyone_is_even():
    assert shopping_balances([ANA, BEN], [], []) == {ANA: 0, BEN: 0}


def test_cost_from_a_non_member_is_rejected():
    with pytest.raises(ValueError):
        shopping_balances([ANA, BEN], [(TOM, 500)], [])


def test_payment_with_a_non_member_is_rejected():
    with pytest.raises(ValueError):
        shopping_balances([ANA, BEN], [], [(TOM, ANA, 500)])


# --- Settling up -------------------------------------------------------------


def test_settle_up_pays_everyone_back():
    balances = {ANA: 2000, BEN: -1000, TOM: -1000}
    assert settle_up(balances) == [(BEN, ANA, 1000), (TOM, ANA, 1000)]


def test_settle_up_with_several_creditors():
    balances = {ANA: 700, BEN: 300, TOM: -1000}
    assert settle_up(balances) == [(TOM, ANA, 700), (TOM, BEN, 300)]


def test_settle_up_leaves_everyone_even():
    balances = shopping_balances([ANA, BEN, TOM], [(ANA, 1000), (BEN, 2501)], [])
    after = dict(balances)
    for payer, receiver, cents in settle_up(balances):
        after[payer] += cents
        after[receiver] -= cents
    assert set(after.values()) == {0}


def test_nothing_to_settle_when_even():
    assert settle_up({ANA: 0, BEN: 0}) == []


# --- Confirming payments -----------------------------------------------------


def test_receiver_can_confirm_a_payment():
    check_payment(payer=BEN, receiver=ANA, confirmed_by=ANA, members=[ANA, BEN])


def test_payer_cannot_confirm_their_own_payment():
    with pytest.raises(ValueError):
        check_payment(payer=BEN, receiver=ANA, confirmed_by=BEN, members=[ANA, BEN])


def test_payment_to_yourself_is_rejected():
    with pytest.raises(ValueError):
        check_payment(payer=ANA, receiver=ANA, confirmed_by=ANA, members=[ANA, BEN])


def test_payment_from_outside_the_flat_is_rejected():
    with pytest.raises(ValueError):
        check_payment(payer=TOM, receiver=ANA, confirmed_by=ANA, members=[ANA, BEN])
