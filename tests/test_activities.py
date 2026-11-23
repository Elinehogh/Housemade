"""Tests for the activity rules (specs/activities.md)."""

from datetime import date, timedelta

import pytest

from logic import (
    MAX_ACTIVITY_LENGTH,
    activity_cost_cents,
    can_afford,
    check_activity_date,
    check_can_remove_activity,
    clean_activity_name,
)

TODAY = date(2026, 11, 23)

# --- Name ------------------------------------------------------------------------


def test_name_is_tidied():
    assert clean_activity_name("  Beach   day ") == "Beach day"


@pytest.mark.parametrize("raw", ["", "   ", "\n"])
def test_empty_name_is_rejected(raw):
    with pytest.raises(ValueError):
        clean_activity_name(raw)


def test_name_at_max_length_is_accepted():
    assert clean_activity_name("a" * MAX_ACTIVITY_LENGTH) == "a" * MAX_ACTIVITY_LENGTH


def test_too_long_name_is_rejected():
    with pytest.raises(ValueError):
        clean_activity_name("a" * (MAX_ACTIVITY_LENGTH + 1))


def test_duplicate_with_other_capitals_and_spaces_is_rejected():
    with pytest.raises(ValueError, match="already"):
        clean_activity_name("  BEACH   day", ["Beach day"])


def test_different_name_is_accepted():
    assert clean_activity_name("Picnic", ["Beach day"]) == "Picnic"


# --- Price -----------------------------------------------------------------------


@pytest.mark.parametrize("raw, cents", [(0, 0), (0.0, 0), (12.5, 1250), ("18.40", 1840), (1000, 100000)])
def test_allowed_prices(raw, cents):
    assert activity_cost_cents(raw) == cents


@pytest.mark.parametrize("raw", [-1, -0.01, 1000.01, 1.234, "cheap", float("nan"), float("inf")])
def test_rejected_prices(raw):
    with pytest.raises(ValueError):
        activity_cost_cents(raw)


# --- Date ------------------------------------------------------------------------


def test_today_is_allowed():
    assert check_activity_date(TODAY, TODAY) == TODAY


def test_future_date_is_allowed():
    later = TODAY + timedelta(days=30)
    assert check_activity_date(later, TODAY) == later


def test_past_date_is_rejected():
    with pytest.raises(ValueError):
        check_activity_date(TODAY - timedelta(days=1), TODAY)


def test_missing_date_is_rejected():
    with pytest.raises(ValueError):
        check_activity_date(None, TODAY)


# --- Who can remove --------------------------------------------------------------


def test_person_who_added_it_can_remove_it():
    check_can_remove_activity(added_by=1, user_id=1, role="member")


def test_admin_can_remove_it():
    check_can_remove_activity(added_by=1, user_id=2, role="admin")


def test_other_member_cannot_remove_it():
    with pytest.raises(ValueError):
        check_can_remove_activity(added_by=1, user_id=2, role="member")


# --- The fund --------------------------------------------------------------------


@pytest.mark.parametrize("cost, balance, expected", [
    (500, 500, True),
    (499, 500, True),
    (501, 500, False),
    (0, 0, True),
    (0, -100, True),
    (1, 0, False),
])
def test_can_afford(cost, balance, expected):
    assert can_afford(cost, balance) is expected
