"""Tests for the chore rules in logic.py. See specs/chores.md."""

from datetime import date

import pytest

from logic import (
    COMMON_CHORES,
    DEFAULT_POINTS,
    MAX_CHORE_LENGTH,
    MAX_POINTS,
    MIN_POINTS,
    check_can_tick_off,
    clean_chore_name,
    clean_points,
    leaderboard,
    suggested_points,
    week_start,
)

ANNA, BEN, CARL = 1, 2, 3


# --- Chore name -------------------------------------------------------------


def test_chore_name_is_tidied():
    assert clean_chore_name("  Clean   bathroom ") == "Clean bathroom"


def test_empty_chore_name_is_rejected():
    with pytest.raises(ValueError):
        clean_chore_name("   ")


def test_chore_name_at_max_length_is_accepted():
    assert clean_chore_name("a" * MAX_CHORE_LENGTH) == "a" * MAX_CHORE_LENGTH


def test_chore_name_over_max_length_is_rejected():
    with pytest.raises(ValueError):
        clean_chore_name("a" * (MAX_CHORE_LENGTH + 1))


# --- Points -----------------------------------------------------------------


def test_lowest_and_highest_points_are_accepted():
    assert clean_points(MIN_POINTS) == MIN_POINTS
    assert clean_points(MAX_POINTS) == MAX_POINTS


def test_whole_number_as_float_is_accepted():
    assert clean_points(3.0) == 3


@pytest.mark.parametrize("points", [0, -1, MAX_POINTS + 1])
def test_points_outside_the_range_are_rejected(points):
    with pytest.raises(ValueError):
        clean_points(points)


def test_points_with_decimals_are_rejected():
    with pytest.raises(ValueError):
        clean_points(2.5)


# --- Ticking off ------------------------------------------------------------


def test_person_given_the_chore_can_tick_it_off():
    check_can_tick_off(assigned_to=ANNA, is_done=False, user_id=ANNA)


def test_someone_else_cannot_tick_off_the_chore():
    with pytest.raises(ValueError):
        check_can_tick_off(assigned_to=ANNA, is_done=False, user_id=BEN)


def test_chore_cannot_be_ticked_off_twice():
    with pytest.raises(ValueError):
        check_can_tick_off(assigned_to=ANNA, is_done=True, user_id=ANNA)


# --- Week -------------------------------------------------------------------


def test_week_starts_on_monday():
    assert week_start(date(2026, 11, 19)) == date(2026, 11, 16)  # Thursday


def test_monday_is_its_own_week_start():
    assert week_start(date(2026, 11, 16)) == date(2026, 11, 16)


def test_sunday_belongs_to_the_week_before():
    assert week_start(date(2026, 11, 22)) == date(2026, 11, 16)


# --- Leaderboard ------------------------------------------------------------


MEMBERS = {ANNA: "Anna", BEN: "Ben", CARL: "Carl"}


def test_points_are_added_up_and_ranked_highest_first():
    done = [(ANNA, 2), (BEN, 5), (ANNA, 1)]
    assert leaderboard(MEMBERS, done) == [("Ben", 5), ("Anna", 3), ("Carl", 0)]


def test_members_without_points_are_shown_with_zero():
    assert leaderboard(MEMBERS, []) == [("Anna", 0), ("Ben", 0), ("Carl", 0)]


def test_equal_points_are_sorted_by_name():
    assert leaderboard(MEMBERS, [(CARL, 3), (ANNA, 3)]) == [("Anna", 3), ("Carl", 3), ("Ben", 0)]


def test_members_with_the_same_name_are_kept_apart():
    twins = {ANNA: "Anna", BEN: "Anna"}
    assert leaderboard(twins, [(ANNA, 2)]) == [("Anna", 2), ("Anna", 0)]


def test_points_for_a_non_member_are_rejected():
    with pytest.raises(ValueError):
        leaderboard(MEMBERS, [(99, 2)])


# --- Common chores -----------------------------------------------------------


def test_common_chores_have_valid_names_and_points():
    assert len({name.lower() for name in COMMON_CHORES}) == len(COMMON_CHORES)
    for name, points in COMMON_CHORES.items():
        assert clean_chore_name(name) == name
        assert clean_points(points) == points


def test_common_chore_gets_its_suggested_points():
    assert suggested_points("Clean the bathroom") == COMMON_CHORES["Clean the bathroom"]


def test_suggested_points_ignore_case_and_spaces():
    assert suggested_points("  take out THE trash ") == COMMON_CHORES["Take out the trash"]


@pytest.mark.parametrize("name", ["Feed the cat", "", None])
def test_own_chore_starts_at_default_points(name):
    assert suggested_points(name) == DEFAULT_POINTS
