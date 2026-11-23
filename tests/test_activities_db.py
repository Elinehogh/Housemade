"""Database tests for activities and votes. Each test gets a fresh in-memory SQLite database, never the real one."""

from datetime import date, timedelta

import pytest
from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError

import db

TODAY = date(2026, 11, 23)
TOMORROW = TODAY + timedelta(days=1)
YESTERDAY = TODAY - timedelta(days=1)


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
def carl(engine):
    """Carl is the admin of another flat."""
    carl = db.get_or_create_user(engine, "carl@example.com", "Carl")
    db.create_flat(engine, carl, "Other flat")
    return carl


def add(engine, user, name="Picnic", cost=15, on=TODAY):
    return db.add_activity(engine, user, name, cost, on, today=TODAY)


# --- Adding ----------------------------------------------------------------------


def test_new_flat_has_no_activities(engine, anna):
    assert db.list_activities(engine, anna) == []


def test_any_member_can_add_an_activity(engine, anna, ben):
    add(engine, ben, "  Beach   day ", 12.5, TOMORROW)
    saved = db.list_activities(engine, anna)[0]
    assert (saved["activity"], saved["cost_cents"], saved["planned_on"]) == ("Beach day", 1250, TOMORROW)
    assert (saved["who"], saved["added_by"], saved["votes"]) == ("Ben", ben, [])


def test_free_activity_is_accepted(engine, anna):
    add(engine, anna, cost=0)
    assert db.list_activities(engine, anna)[0]["cost_cents"] == 0


@pytest.mark.parametrize("name, cost, on", [
    ("   ", 10, TODAY),
    ("a" * 41, 10, TODAY),
    ("Picnic", -1, TODAY),
    ("Picnic", 1000.01, TODAY),
    ("Picnic", 1.234, TODAY),
    ("Picnic", 10, YESTERDAY),
    ("Picnic", 10, None),
])
def test_invalid_activity_is_rejected_and_not_saved(engine, anna, name, cost, on):
    with pytest.raises(ValueError):
        add(engine, anna, name, cost, on)
    assert db.list_activities(engine, anna) == []


def test_duplicate_is_rejected(engine, anna, ben):
    add(engine, anna, "Picnic")
    with pytest.raises(ValueError, match="already"):
        add(engine, ben, "  PICNIC ")
    assert len(db.list_activities(engine, anna)) == 1


def test_two_flats_can_have_the_same_activity(engine, anna, carl):
    add(engine, anna, "Picnic")
    add(engine, carl, "Picnic")
    assert len(db.list_activities(engine, anna)) == len(db.list_activities(engine, carl)) == 1


def test_user_without_a_flat_cannot_add_or_list(engine):
    loner = db.get_or_create_user(engine, "loner@example.com", "Loner")
    with pytest.raises(ValueError):
        add(engine, loner)
    with pytest.raises(ValueError):
        db.list_activities(engine, loner)


# --- Voting ----------------------------------------------------------------------


def test_vote_is_saved_with_the_user_id(engine, anna, ben):
    picnic = add(engine, anna)
    db.vote_for_activity(engine, ben, picnic, today=TODAY)
    assert db.list_activities(engine, anna)[0]["votes"] == [{"user_id": ben, "name": "Ben", "day": TODAY}]


def test_flatmates_with_the_same_name_have_separate_votes(engine, anna):
    first = join(engine, anna, "Sam")
    second = db.get_or_create_user(engine, "other-sam@example.com", "Sam")
    db.join_flat(engine, second, db.get_membership(engine, anna)["invite_code"])
    picnic = add(engine, anna)
    db.vote_for_activity(engine, first, picnic, today=TODAY)
    db.vote_for_activity(engine, second, picnic, today=TODAY)
    assert {vote["user_id"] for vote in db.list_activities(engine, anna)[0]["votes"]} == {first, second}


def test_voting_twice_on_one_activity_is_rejected(engine, anna):
    picnic = add(engine, anna)
    db.vote_for_activity(engine, anna, picnic, today=TODAY)
    with pytest.raises(ValueError, match="already voted"):
        db.vote_for_activity(engine, anna, picnic, today=TOMORROW)
    assert len(db.list_activities(engine, anna)[0]["votes"]) == 1


def test_second_vote_on_the_same_day_is_rejected(engine, anna):
    picnic, beach = add(engine, anna, "Picnic"), add(engine, anna, "Beach")
    db.vote_for_activity(engine, anna, picnic, today=TODAY)
    with pytest.raises(ValueError, match="already voted today"):
        db.vote_for_activity(engine, anna, beach, today=TODAY)


def test_voting_for_another_activity_the_next_day_is_accepted(engine, anna):
    picnic, beach = add(engine, anna, "Picnic"), add(engine, anna, "Beach")
    db.vote_for_activity(engine, anna, picnic, today=TODAY)
    db.vote_for_activity(engine, anna, beach, today=TOMORROW)
    assert sum(len(item["votes"]) for item in db.list_activities(engine, anna)) == 2


def test_list_is_sorted_by_votes_then_name(engine, anna, ben):
    zoo, aquarium, picnic = add(engine, anna, "Zoo"), add(engine, anna, "Aquarium"), add(engine, anna, "Picnic")
    db.vote_for_activity(engine, ben, picnic, today=TODAY)
    assert [item["activity"] for item in db.list_activities(engine, anna)] == ["Picnic", "Aquarium", "Zoo"]
    assert zoo != aquarium


def test_cannot_vote_on_an_activity_that_does_not_exist(engine, anna):
    with pytest.raises(ValueError, match="not on your list"):
        db.vote_for_activity(engine, anna, 999, today=TODAY)


# --- The database refuses duplicates by itself -----------------------------------


def test_database_refuses_a_second_vote_on_the_same_activity(engine, anna):
    picnic = add(engine, anna)
    with engine.begin() as conn:
        conn.execute(insert(db.activity_votes).values(activity_id=picnic, user_id=anna, voted_on=TODAY))
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(insert(db.activity_votes).values(activity_id=picnic, user_id=anna, voted_on=TOMORROW))


def test_database_refuses_a_second_vote_on_the_same_day(engine, anna):
    picnic, beach = add(engine, anna, "Picnic"), add(engine, anna, "Beach")
    with engine.begin() as conn:
        conn.execute(insert(db.activity_votes).values(activity_id=picnic, user_id=anna, voted_on=TODAY))
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(insert(db.activity_votes).values(activity_id=beach, user_id=anna, voted_on=TODAY))


def test_database_refuses_a_duplicate_activity_in_one_flat(engine, anna):
    add(engine, anna, "Picnic")
    flat_id = db.get_membership(engine, anna)["flat_id"]
    values = dict(flat_id=flat_id, name="PICNIC", name_key="picnic", cost_cents=0, planned_on=TODAY,
                  added_by=anna, created_at=db.datetime(2026, 11, 23))
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(insert(db.activities).values(**values))


# --- Removing --------------------------------------------------------------------


def test_person_who_added_it_can_remove_it(engine, anna, ben):
    picnic = add(engine, ben)
    db.remove_activity(engine, ben, picnic)
    assert db.list_activities(engine, anna) == []


def test_admin_can_remove_someone_elses_activity(engine, anna, ben):
    picnic = add(engine, ben)
    db.remove_activity(engine, anna, picnic)
    assert db.list_activities(engine, anna) == []


def test_other_member_cannot_remove_it(engine, anna, ben, cleo):
    picnic = add(engine, ben)
    with pytest.raises(ValueError):
        db.remove_activity(engine, cleo, picnic)
    assert len(db.list_activities(engine, anna)) == 1


def test_removing_also_removes_its_votes_and_gives_the_days_vote_back(engine, anna, ben):
    picnic, beach = add(engine, ben, "Picnic"), add(engine, ben, "Beach")
    db.vote_for_activity(engine, anna, picnic, today=TODAY)
    db.remove_activity(engine, ben, picnic)
    db.vote_for_activity(engine, anna, beach, today=TODAY)
    assert [vote["user_id"] for vote in db.list_activities(engine, anna)[0]["votes"]] == [anna]


def test_removed_activity_can_be_added_again_without_old_votes(engine, anna):
    picnic = add(engine, anna)
    db.vote_for_activity(engine, anna, picnic, today=TODAY)
    db.remove_activity(engine, anna, picnic)
    add(engine, anna)
    assert db.list_activities(engine, anna)[0]["votes"] == []


def test_removing_an_activity_that_does_not_exist_is_rejected(engine, anna):
    with pytest.raises(ValueError, match="not on your list"):
        db.remove_activity(engine, anna, 999)


# --- Another flat ----------------------------------------------------------------


def test_another_flat_does_not_see_the_list_or_votes(engine, anna, carl):
    picnic = add(engine, anna)
    db.vote_for_activity(engine, anna, picnic, today=TODAY)
    assert db.list_activities(engine, carl) == []


def test_another_flat_cannot_vote(engine, anna, carl):
    picnic = add(engine, anna)
    with pytest.raises(ValueError, match="not on your list"):
        db.vote_for_activity(engine, carl, picnic, today=TODAY)
    assert db.list_activities(engine, anna)[0]["votes"] == []


def test_another_flats_admin_cannot_remove(engine, anna, carl):
    picnic = add(engine, anna)
    with pytest.raises(ValueError, match="not on your list"):
        db.remove_activity(engine, carl, picnic)
    assert len(db.list_activities(engine, anna)) == 1


def test_votes_in_another_flat_do_not_use_up_your_vote(engine, anna, carl):
    ours, theirs = add(engine, anna), add(engine, carl)
    db.vote_for_activity(engine, carl, theirs, today=TODAY)
    db.vote_for_activity(engine, anna, ours, today=TODAY)
    assert len(db.list_activities(engine, anna)[0]["votes"]) == 1
    assert len(db.list_activities(engine, carl)[0]["votes"]) == 1
