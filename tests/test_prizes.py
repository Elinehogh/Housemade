"""Tests for the weekly prize rules (specs/weekly-prize.md)."""

from datetime import date, timedelta

import pytest

from logic import (
    MAX_PRIZE_LENGTH,
    MAX_PRIZES_PER_KIND,
    check_can_suggest_prize,
    check_can_vote_prize,
    chosen_prize,
    clean_prize,
    voting_is_open,
    week_result,
)

MONDAY = date(2026, 11, 23)
WEDNESDAY = MONDAY + timedelta(days=2)
THURSDAY = MONDAY + timedelta(days=3)
SUNDAY = MONDAY + timedelta(days=6)
LAST_MONDAY = MONDAY - timedelta(days=7)

# --- When voting is open ---------------------------------------------------------


@pytest.mark.parametrize("offset, expected", [(0, True), (1, True), (2, True), (3, False), (4, False), (5, False), (6, False)])
def test_voting_is_open_monday_to_wednesday(offset, expected):
    assert voting_is_open(MONDAY + timedelta(days=offset)) is expected


# --- A suggestion ----------------------------------------------------------------


def test_suggestion_is_tidied():
    assert clean_prize("  Cook   dinner ") == "Cook dinner"


@pytest.mark.parametrize("raw", ["", "   ", "\n"])
def test_empty_suggestion_is_rejected(raw):
    with pytest.raises(ValueError):
        clean_prize(raw)


def test_suggestion_at_max_length_is_accepted():
    assert clean_prize("a" * MAX_PRIZE_LENGTH) == "a" * MAX_PRIZE_LENGTH


def test_too_long_suggestion_is_rejected():
    with pytest.raises(ValueError):
        clean_prize("a" * (MAX_PRIZE_LENGTH + 1))


def test_duplicate_with_other_capitals_and_spaces_is_rejected():
    with pytest.raises(ValueError, match="already"):
        clean_prize("  COOK   dinner", ["Cook dinner"])


@pytest.mark.parametrize("day", [MONDAY, WEDNESDAY])
def test_can_suggest_while_voting_is_open(day):
    check_can_suggest_prize("winner", 0, day)
    check_can_suggest_prize("loser", MAX_PRIZES_PER_KIND - 1, day)


def test_cannot_suggest_after_wednesday():
    with pytest.raises(ValueError, match="closed"):
        check_can_suggest_prize("winner", 0, THURSDAY)


def test_cannot_suggest_too_many():
    with pytest.raises(ValueError, match="at most"):
        check_can_suggest_prize("loser", MAX_PRIZES_PER_KIND, MONDAY)


def test_unknown_kind_is_rejected():
    with pytest.raises(ValueError):
        check_can_suggest_prize("runner-up", 0, MONDAY)


# --- A vote ----------------------------------------------------------------------


def test_first_vote_is_accepted():
    check_can_vote_prize(MONDAY, False, WEDNESDAY)


def test_second_vote_is_rejected():
    with pytest.raises(ValueError, match="already voted"):
        check_can_vote_prize(MONDAY, True, MONDAY)


def test_vote_after_wednesday_is_rejected():
    with pytest.raises(ValueError, match="closed"):
        check_can_vote_prize(MONDAY, False, THURSDAY)


def test_vote_on_last_weeks_option_is_rejected():
    with pytest.raises(ValueError, match="this week"):
        check_can_vote_prize(LAST_MONDAY, False, MONDAY)


# --- The chosen option -----------------------------------------------------------


def option(option_id, votes):
    return {"id": option_id, "votes": list(range(votes))}


def test_most_votes_wins():
    assert chosen_prize([option(1, 1), option(2, 3), option(3, 2)])["id"] == 2


def test_tie_goes_to_the_first_suggested():
    assert chosen_prize([option(5, 2), option(2, 2), option(9, 1)])["id"] == 2


def test_no_votes_means_no_deal():
    assert chosen_prize([option(1, 0), option(2, 0)]) is None


def test_no_options_means_no_deal():
    assert chosen_prize([]) is None


# --- Winners and losers ----------------------------------------------------------


def test_top_and_bottom_of_the_leaderboard():
    assert week_result([("Ana", 15), ("You", 12), ("Tom", 8)]) == {"winners": ["Ana"], "losers": ["Tom"]}


def test_ties_share_the_result():
    ranking = [("Ana", 9), ("Ben", 9), ("Cleo", 4), ("Dan", 1), ("Eli", 1)]
    assert week_result(ranking) == {"winners": ["Ana", "Ben"], "losers": ["Dan", "Eli"]}


def test_everyone_equal_has_no_winner_or_loser():
    assert week_result([("Ana", 5), ("Ben", 5)]) == {"winners": [], "losers": []}


def test_nobody_did_anything_has_no_winner_or_loser():
    assert week_result([("Ana", 0), ("Ben", 0)]) == {"winners": [], "losers": []}


def test_one_member_has_no_winner_or_loser():
    assert week_result([("Ana", 10)]) == {"winners": [], "losers": []}


def test_empty_leaderboard():
    assert week_result([]) == {"winners": [], "losers": []}
