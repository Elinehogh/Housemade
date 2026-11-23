"""Database tests for the house rules. Each test gets a fresh in-memory SQLite database, never the real one."""

from datetime import datetime

import pytest

import db

MONDAY = datetime(2026, 11, 23, 12, 0)


@pytest.fixture
def engine():
    engine = db.engine_from_url("sqlite://")
    db.create_tables(engine)
    return engine


@pytest.fixture
def anna(engine):
    """Anna is the admin of her flat."""
    anna = db.get_or_create_user(engine, "anna@example.com", "Anna")
    db.create_flat(engine, anna, "Rua Augusta 12")
    return anna


def join(engine, anna, name):
    member = db.get_or_create_user(engine, f"{name.lower()}@example.com", name)
    db.join_flat(engine, member, db.get_membership(engine, anna)["invite_code"])
    return member


@pytest.fixture
def ben(engine, anna):
    return join(engine, anna, "Ben")


@pytest.fixture
def cleo(engine, anna):
    return join(engine, anna, "Cleo")


@pytest.fixture
def dan(engine, anna):
    return join(engine, anna, "Dan")


@pytest.fixture
def carl(engine):
    """Carl is the admin of another flat."""
    carl = db.get_or_create_user(engine, "carl@example.com", "Carl")
    db.create_flat(engine, carl, "Other flat")
    return carl


# --- Adding ----------------------------------------------------------------------


def test_new_flat_has_no_rules(engine, anna):
    assert db.list_rules(engine, anna) == []


def test_any_member_can_add_a_rule(engine, anna, ben):
    db.add_rule(engine, ben, "  No   shoes inside ", now=MONDAY)
    rule = db.list_rules(engine, anna)[0]
    assert (rule["text"], rule["who"], rule["added_at"]) == ("No shoes inside", "Ben", MONDAY)
    assert rule["voters"] == []


def test_rules_are_listed_oldest_first(engine, anna, ben):
    db.add_rule(engine, ben, "First")
    db.add_rule(engine, anna, "Second")
    assert [rule["text"] for rule in db.list_rules(engine, anna)] == ["First", "Second"]


def test_empty_rule_is_rejected(engine, anna):
    with pytest.raises(ValueError):
        db.add_rule(engine, anna, "   ")
    assert db.list_rules(engine, anna) == []


def test_too_long_rule_is_rejected(engine, anna):
    with pytest.raises(ValueError):
        db.add_rule(engine, anna, "a" * 121)


def test_duplicate_rule_is_rejected(engine, anna, ben):
    db.add_rule(engine, anna, "No shoes inside")
    with pytest.raises(ValueError, match="already"):
        db.add_rule(engine, ben, "NO SHOES inside")
    assert len(db.list_rules(engine, anna)) == 1


def test_two_flats_can_have_the_same_rule(engine, anna, carl):
    db.add_rule(engine, anna, "No shoes inside")
    db.add_rule(engine, carl, "No shoes inside")
    assert len(db.list_rules(engine, anna)) == len(db.list_rules(engine, carl)) == 1


def test_user_without_a_flat_cannot_add_a_rule(engine):
    loner = db.get_or_create_user(engine, "loner@example.com", "Loner")
    with pytest.raises(ValueError):
        db.add_rule(engine, loner, "No shoes inside")


# --- Who sees what ---------------------------------------------------------------


def test_members_only_see_their_own_flats_rules(engine, anna, carl):
    db.add_rule(engine, anna, "No shoes inside")
    assert db.list_rules(engine, carl) == []


def test_user_without_a_flat_cannot_list_rules(engine):
    loner = db.get_or_create_user(engine, "loner@example.com", "Loner")
    with pytest.raises(ValueError):
        db.list_rules(engine, loner)


# --- Voting ----------------------------------------------------------------------


def test_vote_is_counted_with_the_voters_name(engine, anna, ben, cleo, dan):
    rule = db.add_rule(engine, anna, "No shoes inside")
    assert db.vote_to_remove(engine, ben, rule) is False
    saved = db.list_rules(engine, anna)[0]
    assert saved["voters"] == ["Ben"]
    assert saved["voter_ids"] == [ben]
    assert saved["votes_needed"] == 3


def test_voting_twice_is_rejected_and_counts_once(engine, anna, ben, cleo, dan):
    rule = db.add_rule(engine, anna, "No shoes inside")
    db.vote_to_remove(engine, ben, rule)
    with pytest.raises(ValueError, match="already voted"):
        db.vote_to_remove(engine, ben, rule)
    assert db.list_rules(engine, anna)[0]["voters"] == ["Ben"]


def test_one_person_cannot_remove_a_rule_alone(engine, anna, ben, cleo):
    rule = db.add_rule(engine, anna, "No shoes inside")
    assert db.vote_to_remove(engine, anna, rule) is False
    assert len(db.list_rules(engine, anna)) == 1


def test_half_of_the_flat_is_not_enough(engine, anna, ben, cleo, dan):
    rule = db.add_rule(engine, anna, "No shoes inside")
    db.vote_to_remove(engine, anna, rule)
    assert db.vote_to_remove(engine, ben, rule) is False
    assert len(db.list_rules(engine, anna)) == 1


def test_rule_is_removed_at_the_majority(engine, anna, ben, cleo, dan):
    rule = db.add_rule(engine, anna, "No shoes inside")
    db.vote_to_remove(engine, anna, rule)
    db.vote_to_remove(engine, ben, rule)
    assert db.vote_to_remove(engine, cleo, rule) is True
    assert db.list_rules(engine, anna) == []


def test_only_member_of_a_flat_can_remove_alone(engine, anna):
    rule = db.add_rule(engine, anna, "No shoes inside")
    assert db.vote_to_remove(engine, anna, rule) is True


def test_votes_on_one_rule_do_not_count_for_another(engine, anna, ben, cleo):
    first = db.add_rule(engine, anna, "First")
    second = db.add_rule(engine, anna, "Second")
    db.vote_to_remove(engine, anna, first)
    assert db.vote_to_remove(engine, ben, second) is False
    assert [len(rule["voters"]) for rule in db.list_rules(engine, anna)] == [1, 1]


def test_removed_rule_can_be_added_again_without_old_votes(engine, anna, ben):
    rule = db.add_rule(engine, anna, "No shoes inside")
    db.vote_to_remove(engine, anna, rule)
    db.vote_to_remove(engine, ben, rule)
    db.add_rule(engine, ben, "No shoes inside")
    assert db.list_rules(engine, anna)[0]["voters"] == []


def test_cannot_vote_on_another_flats_rule(engine, anna, carl):
    rule = db.add_rule(engine, anna, "No shoes inside")
    with pytest.raises(ValueError, match="not on your list"):
        db.vote_to_remove(engine, carl, rule)
    assert db.list_rules(engine, anna)[0]["voters"] == []


def test_cannot_vote_on_a_rule_that_does_not_exist(engine, anna):
    with pytest.raises(ValueError, match="not on your list"):
        db.vote_to_remove(engine, anna, 999)


def test_cannot_vote_on_a_rule_that_was_just_removed(engine, anna, ben, cleo):
    rule = db.add_rule(engine, anna, "No shoes inside")
    db.vote_to_remove(engine, anna, rule)
    db.vote_to_remove(engine, ben, rule)
    with pytest.raises(ValueError, match="not on your list"):
        db.vote_to_remove(engine, cleo, rule)
