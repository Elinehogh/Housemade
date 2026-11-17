"""Tests for the fund rules in logic.py. See specs/fund.md."""

import csv
import io
from datetime import date

import pytest

from logic import (
    MAX_DESCRIPTION_LENGTH,
    MAX_FUND_AMOUNT,
    check_can_take_out,
    clean_description,
    format_euros,
    fund_csv,
    goal_progress,
    to_cents,
)

# --- Amounts ----------------------------------------------------------------


def test_amount_is_stored_as_cents():
    assert to_cents(6.4) == 640


def test_amount_is_rounded_to_cents():
    assert to_cents(2.999) == 300


def test_smallest_and_largest_amounts_are_accepted():
    assert to_cents(0.01) == 1
    assert to_cents(MAX_FUND_AMOUNT) == MAX_FUND_AMOUNT * 100


@pytest.mark.parametrize("amount", [0, -5, 0.004, MAX_FUND_AMOUNT + 0.01])
def test_amounts_outside_the_range_are_rejected(amount):
    with pytest.raises(ValueError):
        to_cents(amount)


@pytest.mark.parametrize("cents, text", [(640, "€6.40"), (5, "€0.05"), (0, "€0.00"), (-2400, "-€24.00")])
def test_cents_are_shown_as_euros(cents, text):
    assert format_euros(cents) == text


# --- Description ------------------------------------------------------------


def test_description_is_tidied():
    assert clean_description("  Pizza   night ") == "Pizza night"


def test_empty_description_is_rejected():
    with pytest.raises(ValueError):
        clean_description("  ")


def test_description_at_max_length_is_accepted():
    assert clean_description("a" * MAX_DESCRIPTION_LENGTH) == "a" * MAX_DESCRIPTION_LENGTH


def test_description_over_max_length_is_rejected():
    with pytest.raises(ValueError):
        clean_description("a" * (MAX_DESCRIPTION_LENGTH + 1))


# --- The fund cannot go below zero ------------------------------------------


def test_taking_out_less_than_the_balance_is_allowed():
    check_can_take_out(balance_cents=1000, amount_cents=999)


def test_taking_out_exactly_the_balance_is_allowed():
    check_can_take_out(balance_cents=1000, amount_cents=1000)


def test_taking_out_more_than_the_balance_is_rejected():
    with pytest.raises(ValueError):
        check_can_take_out(balance_cents=1000, amount_cents=1001)


def test_nothing_can_be_taken_out_of_an_empty_fund():
    with pytest.raises(ValueError):
        check_can_take_out(balance_cents=0, amount_cents=1)


# --- Goal -------------------------------------------------------------------


def test_goal_progress_is_a_fraction():
    assert goal_progress(2000, 8000) == 0.25


def test_goal_progress_stops_at_full():
    assert goal_progress(9000, 8000) == 1.0


def test_goal_progress_of_empty_fund_is_zero():
    assert goal_progress(0, 8000) == 0.0


# --- CSV export -------------------------------------------------------------


def test_csv_has_a_header_and_one_row_per_entry():
    entries = [
        {"date": date(2026, 11, 17), "what": "Pant", "who": "Anna", "cents": 640},
        {"date": date(2026, 11, 18), "what": "Pizza, cola", "who": "Ben", "cents": -500},
    ]
    rows = list(csv.reader(io.StringIO(fund_csv(entries))))
    assert rows == [
        ["date", "what", "who", "amount_eur"],
        ["2026-11-17", "Pant", "Anna", "6.40"],
        ["2026-11-18", "Pizza, cola", "Ben", "-5.00"],
    ]


def test_csv_of_empty_history_has_only_the_header():
    assert fund_csv([]).strip() == "date,what,who,amount_eur"
