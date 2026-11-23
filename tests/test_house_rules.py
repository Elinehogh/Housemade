"""Tests for the house rules (specs/house-rules.md)."""

import pytest

from logic import MAX_RULE_LENGTH, check_can_vote_to_remove, clean_rule, has_majority, votes_needed

# --- A new rule ------------------------------------------------------------------


def test_rule_is_tidied():
    assert clean_rule("  No   shoes inside ") == "No shoes inside"


@pytest.mark.parametrize("raw", ["", "    ", "\n\t"])
def test_empty_rule_is_rejected(raw):
    with pytest.raises(ValueError):
        clean_rule(raw)


def test_rule_at_max_length_is_accepted():
    assert clean_rule("a" * MAX_RULE_LENGTH) == "a" * MAX_RULE_LENGTH


def test_too_long_rule_is_rejected():
    with pytest.raises(ValueError):
        clean_rule("a" * (MAX_RULE_LENGTH + 1))


def test_duplicate_rule_is_rejected():
    with pytest.raises(ValueError, match="already"):
        clean_rule("No shoes inside", ["Quiet after 23:00", "No shoes inside"])


def test_duplicate_with_other_capitals_and_spaces_is_rejected():
    with pytest.raises(ValueError, match="already"):
        clean_rule("  NO  shoes INSIDE", ["No shoes inside"])


def test_different_rule_is_accepted():
    assert clean_rule("No shoes inside", ["Quiet after 23:00"]) == "No shoes inside"


# --- The majority ----------------------------------------------------------------


@pytest.mark.parametrize("members, needed", [(1, 1), (2, 2), (3, 2), (4, 3), (5, 3), (6, 4)])
def test_votes_needed_is_more_than_half(members, needed):
    assert votes_needed(members) == needed


def test_flat_without_members_is_rejected():
    with pytest.raises(ValueError):
        votes_needed(0)


def test_exactly_half_is_not_a_majority():
    assert not has_majority(2, 4)


def test_more_than_half_is_a_majority():
    assert has_majority(3, 4)


def test_no_votes_is_not_a_majority():
    assert not has_majority(0, 1)


# --- One vote each ---------------------------------------------------------------


def test_first_vote_is_accepted():
    check_can_vote_to_remove([], "Ana")


def test_vote_next_to_other_peoples_votes_is_accepted():
    check_can_vote_to_remove(["Tom", "Sara"], "Ana")


def test_voting_twice_is_rejected():
    with pytest.raises(ValueError, match="already voted"):
        check_can_vote_to_remove(["Tom", "Ana"], "Ana")
