"""Tests for what is waiting for a member's vote on the Today tab (specs/votes-waiting.md)."""

from datetime import date, timedelta

import pytest

import db
from logic import votes_waiting

ME, ANA, TOM = 1, 2, 3
MONDAY = date(2026, 11, 23)
WEDNESDAY = MONDAY + timedelta(days=2)
THURSDAY = MONDAY + timedelta(days=3)
YESTERDAY = MONDAY - timedelta(days=1)


def option(option_id, name="Option", voters=()):
    return {"id": option_id, "name": name, "votes": [{"user_id": v, "name": f"User {v}"} for v in voters]}


def activity(activity_id, name="Picnic", on=MONDAY, votes=()):
    return {
        "id": activity_id, "activity": name, "planned_on": on,
        "votes": [{"user_id": who, "name": f"User {who}", "day": day} for who, day in votes],
    }


def rule(rule_id, voters=(ANA,)):
    return {"id": rule_id, "text": "No shoes", "voters": [f"User {v}" for v in voters], "voter_ids": list(voters)}


def waiting(prizes=None, activities=(), rules=(), today=MONDAY, skipped=()):
    prize_options = {"winner": [], "loser": [], **(prizes or {})}
    return votes_waiting(prize_options, list(activities), list(rules), ME, today, 3, skipped)


def kinds(items):
    return [item["type"] for item in items]


# --- Weekly prize ----------------------------------------------------------------


def test_prize_vote_is_waiting_with_its_options():
    items = waiting({"winner": [option(1, "A free beer", [ANA]), option(2, "Movie")]})
    assert kinds(items) == ["prize"]
    assert items[0]["question"] == "What should this week's winner get?"
    assert [(c["id"], c["label"], c["votes"]) for c in items[0]["choices"]] == [
        (1, "A free beer", 1), (2, "Movie", 0),
    ]


def test_each_of_the_two_prize_votes_is_waiting():
    items = waiting({"winner": [option(1)], "loser": [option(2)]})
    assert [item["question"] for item in items] == [
        "What should this week's winner get?", "What should this week's loser have to do?",
    ]


def test_prize_with_no_options_is_not_waiting():
    assert waiting() == []


def test_prize_already_voted_on_is_not_waiting():
    assert waiting({"winner": [option(1, voters=[ME]), option(2)]}) == []


def test_voting_in_one_prize_vote_leaves_the_other_waiting():
    items = waiting({"winner": [option(1, voters=[ME])], "loser": [option(2)]})
    assert [item["question"] for item in items] == ["What should this week's loser have to do?"]


def test_prize_is_not_waiting_after_wednesday():
    assert waiting({"winner": [option(1)]}, today=THURSDAY) == []


def test_prize_says_when_voting_closes():
    prizes = {"winner": [option(1)]}
    assert waiting(prizes, today=MONDAY)[0]["note"] == "Voting closes Wednesday"
    assert waiting(prizes, today=WEDNESDAY)[0]["note"] == "Voting closes tonight"


# --- House rules -----------------------------------------------------------------


def test_rule_someone_wants_removed_is_waiting():
    items = waiting(rules=[rule(7, [ANA, TOM])])
    assert kinds(items) == ["rule"]
    assert items[0]["question"] == 'Remove the rule "No shoes"?'
    assert items[0]["note"] == "2 of 3 votes so far: User 2, User 3"
    assert [(c["id"], c["label"]) for c in items[0]["choices"]] == [(7, "Vote to remove")]


def test_rule_without_votes_is_not_waiting():
    assert waiting(rules=[rule(7, [])]) == []


def test_rule_i_voted_on_is_not_waiting():
    assert waiting(rules=[rule(7, [ANA, ME])]) == []


# --- Activities ------------------------------------------------------------------


def test_activity_vote_is_waiting():
    items = waiting(activities=[activity(1, "Picnic", votes=[(ANA, MONDAY)]), activity(2, "Beach")])
    assert kinds(items) == ["activity"]
    assert [(c["id"], c["label"], c["votes"]) for c in items[0]["choices"]] == [(1, "Picnic", 1), (2, "Beach", 0)]
    assert items[0]["more"] == 0


def test_no_activities_is_not_waiting():
    assert waiting(activities=[]) == []


def test_used_todays_vote_is_not_waiting():
    assert waiting(activities=[activity(1, votes=[(ME, MONDAY)]), activity(2, "Beach")]) == []


def test_vote_from_yesterday_leaves_other_activities_waiting():
    items = waiting(activities=[activity(1, "Picnic", votes=[(ME, YESTERDAY)]), activity(2, "Beach")])
    assert [c["id"] for c in items[0]["choices"]] == [2]


def test_all_activities_already_voted_for_is_not_waiting():
    assert waiting(activities=[activity(1, votes=[(ME, YESTERDAY)])]) == []


def test_past_activities_are_not_offered():
    items = waiting(activities=[activity(1, "Old", on=YESTERDAY), activity(2, "Beach")])
    assert [c["id"] for c in items[0]["choices"]] == [2]


def test_only_past_activities_is_not_waiting():
    assert waiting(activities=[activity(1, on=YESTERDAY)]) == []


def test_at_most_three_activities_are_offered():
    items = waiting(activities=[activity(n, f"Plan {n}") for n in range(1, 6)])
    assert [c["id"] for c in items[0]["choices"]] == [1, 2, 3]
    assert items[0]["more"] == 2


# --- Not now and the order -------------------------------------------------------


def test_not_now_hides_only_that_item():
    all_items = waiting({"winner": [option(1)], "loser": [option(2)]}, rules=[rule(7)])
    skipped = {all_items[0]["key"]}
    left = waiting({"winner": [option(1)], "loser": [option(2)]}, rules=[rule(7)], skipped=skipped)
    assert [item["key"] for item in left] == [item["key"] for item in all_items[1:]]


def test_keys_change_with_the_week_and_the_day():
    this_week = waiting({"winner": [option(1)]}, activities=[activity(1, on=WEDNESDAY)], today=MONDAY)
    later = waiting({"winner": [option(1)]}, activities=[activity(1, on=WEDNESDAY)], today=WEDNESDAY)
    next_week = waiting({"winner": [option(1)]}, today=MONDAY + timedelta(days=7))
    assert this_week[0]["key"] == later[0]["key"] != next_week[0]["key"]
    assert this_week[1]["key"] != later[1]["key"]


def test_most_urgent_comes_first():
    items = waiting({"winner": [option(1)], "loser": [option(2)]}, [activity(3)], [rule(7)])
    assert kinds(items) == ["prize", "prize", "rule", "activity"]


# --- From the database -----------------------------------------------------------


@pytest.fixture
def engine():
    engine = db.engine_from_url("sqlite://")
    db.create_tables(engine)
    return engine


@pytest.fixture
def anna(engine):
    anna = db.get_or_create_user(engine, "anna@example.com", "Anna")
    db.create_flat(engine, anna, "Rua Augusta 12")
    return anna


@pytest.fixture
def ben(engine, anna):
    ben = db.get_or_create_user(engine, "ben@example.com", "Ben")
    db.join_flat(engine, ben, db.get_membership(engine, anna)["invite_code"])
    return ben


@pytest.fixture
def cleo(engine, anna):
    cleo = db.get_or_create_user(engine, "cleo@example.com", "Cleo")
    db.join_flat(engine, cleo, db.get_membership(engine, anna)["invite_code"])
    return cleo


@pytest.fixture
def carl(engine):
    carl = db.get_or_create_user(engine, "carl@example.com", "Carl")
    db.create_flat(engine, carl, "Other flat")
    return carl


def waiting_for(engine, user, today=MONDAY):
    data = db.today_overview(engine, user, today)
    return votes_waiting(data["prize_options"], data["activities"], data["rules_in_vote"], user, today, data["votes_needed"])


def fill(engine, anna):
    beer = db.add_prize(engine, anna, "winner", "A free beer", today=MONDAY)
    picnic = db.add_activity(engine, anna, "Picnic", 15, MONDAY, today=MONDAY)
    shoes = db.add_rule(engine, anna, "No shoes")
    db.vote_prize(engine, anna, beer, today=MONDAY)
    db.vote_for_activity(engine, anna, picnic, today=MONDAY)
    db.vote_to_remove(engine, anna, shoes)
    return beer, picnic, shoes


def test_flatmate_sees_what_is_waiting(engine, anna, ben, cleo):
    fill(engine, anna)
    assert kinds(waiting_for(engine, ben)) == ["prize", "rule", "activity"]


def test_rule_note_uses_the_real_majority(engine, anna, ben, cleo):
    fill(engine, anna)
    rule_item = next(item for item in waiting_for(engine, ben) if item["type"] == "rule")
    assert rule_item["note"] == "1 of 2 votes so far: Anna"


def test_nothing_is_waiting_for_the_one_who_voted_on_everything(engine, anna, ben, cleo):
    fill(engine, anna)
    assert waiting_for(engine, anna) == []


def test_voting_clears_it_from_the_list(engine, anna, ben, cleo):
    beer, picnic, shoes = fill(engine, anna)
    db.vote_prize(engine, ben, beer, today=MONDAY)
    db.vote_for_activity(engine, ben, picnic, today=MONDAY)
    assert kinds(waiting_for(engine, ben)) == ["rule"]


def test_last_weeks_prize_options_are_not_waiting(engine, anna, ben):
    db.add_prize(engine, anna, "winner", "A free beer", today=MONDAY)
    assert waiting_for(engine, ben, MONDAY + timedelta(days=7)) == []


def test_another_flats_votes_never_show_up(engine, anna, ben, carl):
    fill(engine, anna)
    data = db.today_overview(engine, carl, MONDAY)
    assert data["prize_options"] == {"winner": [], "loser": []}
    assert data["rules_in_vote"] == []
    assert waiting_for(engine, carl) == []
