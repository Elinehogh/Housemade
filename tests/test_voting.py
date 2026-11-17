"""Tests for voting on activities (specs/activity-voting.md)."""

from datetime import date, timedelta

import pytest

from logic import check_can_vote, rank_activities, voters

TODAY = date(2026, 11, 17)
YESTERDAY = TODAY - timedelta(days=1)
ACTIVITIES = ["Picnic", "Beach day", "Movie night"]


def vote(activity, who, day=YESTERDAY):
    return {"activity": activity, "who": who, "day": day}


# --- Who may vote --------------------------------------------------------------

def test_first_vote_is_accepted():
    check_can_vote(ACTIVITIES, [], "Picnic", "Ana", TODAY)


def test_voting_twice_for_the_same_activity_is_rejected():
    with pytest.raises(ValueError, match="already voted for Picnic"):
        check_can_vote(ACTIVITIES, [vote("Picnic", "Ana")], "Picnic", "Ana", TODAY)


def test_second_vote_on_the_same_day_is_rejected():
    with pytest.raises(ValueError, match="already voted today"):
        check_can_vote(ACTIVITIES, [vote("Picnic", "Ana", TODAY)], "Beach day", "Ana", TODAY)


def test_message_names_the_activity_voted_for_today():
    with pytest.raises(ValueError, match="Picnic"):
        check_can_vote(ACTIVITIES, [vote("Picnic", "Ana", TODAY)], "Beach day", "Ana", TODAY)


def test_voting_again_the_next_day_is_accepted():
    check_can_vote(ACTIVITIES, [vote("Picnic", "Ana", YESTERDAY)], "Beach day", "Ana", TODAY)


def test_other_peoples_votes_today_do_not_count():
    votes = [vote("Picnic", "Tom", TODAY), vote("Beach day", "Sara", TODAY)]
    check_can_vote(ACTIVITIES, votes, "Picnic", "Ana", TODAY)


def test_vote_for_activity_not_on_the_list_is_rejected():
    with pytest.raises(ValueError, match="not on the list"):
        check_can_vote(ACTIVITIES, [], "Skydiving", "Ana", TODAY)


# --- Who voted -----------------------------------------------------------------

def test_voters_are_listed_in_the_order_they_voted():
    votes = [vote("Picnic", "Tom"), vote("Beach day", "Ana"), vote("Picnic", "Sara", TODAY)]
    assert voters(votes, "Picnic") == ["Tom", "Sara"]


def test_activity_without_votes_has_no_voters():
    assert voters([vote("Picnic", "Tom")], "Movie night") == []


# --- Sorting -------------------------------------------------------------------

def test_activities_are_sorted_by_votes_then_name():
    activities = [{"activity": name, "cost": 0} for name in ("Movie night", "Picnic", "Beach day")]
    votes = [vote("Picnic", "Tom"), vote("Picnic", "Ana", TODAY), vote("Movie night", "Sara")]
    ranked = rank_activities(activities, votes)
    assert [(a["activity"], names) for a, names in ranked] == [
        ("Picnic", ["Tom", "Ana"]),
        ("Movie night", ["Sara"]),
        ("Beach day", []),
    ]


def test_ties_are_sorted_by_name():
    activities = [{"activity": name, "cost": 0} for name in ("Zoo", "Aquarium")]
    assert [a["activity"] for a, _ in rank_activities(activities, [])] == ["Aquarium", "Zoo"]
