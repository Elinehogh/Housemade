"""Database tests. Each test gets a fresh in-memory SQLite database, never the real one."""

import pytest
from sqlalchemy import func, select

import db


@pytest.fixture
def engine():
    engine = db.engine_from_url("sqlite://")
    db.create_tables(engine)
    return engine


@pytest.fixture
def anna(engine):
    return db.get_or_create_user(engine, "anna@example.com", "Anna")


@pytest.fixture
def ben(engine):
    return db.get_or_create_user(engine, "ben@example.com", "Ben")


def count(engine, table):
    with engine.connect() as conn:
        return conn.scalar(select(func.count()).select_from(table))


def test_same_email_gives_same_user(engine, anna):
    assert db.get_or_create_user(engine, " ANNA@example.com ", "Anna") == anna
    assert count(engine, db.users) == 1


def test_user_without_flat_has_no_membership(engine, anna):
    assert db.get_membership(engine, anna) is None
    assert db.list_members(engine, anna) == []


def test_creating_a_flat_makes_the_user_admin(engine, anna):
    code = db.create_flat(engine, anna, "Rua Augusta 12")
    membership = db.get_membership(engine, anna)
    assert membership["flat_name"] == "Rua Augusta 12"
    assert membership["invite_code"] == code
    assert membership["role"] == "admin"


def test_invalid_flat_name_creates_nothing(engine, anna):
    with pytest.raises(ValueError):
        db.create_flat(engine, anna, "   ")
    assert count(engine, db.flats) == 0
    assert db.get_membership(engine, anna) is None


def test_user_cannot_create_a_second_flat(engine, anna):
    db.create_flat(engine, anna, "First")
    with pytest.raises(ValueError):
        db.create_flat(engine, anna, "Second")
    assert count(engine, db.flats) == 1


def test_duplicate_invite_code_is_replaced(engine, anna, ben):
    codes = iter(["AAAAAA", "AAAAAA", "BBBBBB"])
    db.create_flat(engine, anna, "First", make_code=lambda: next(codes))
    assert db.create_flat(engine, ben, "Second", make_code=lambda: next(codes)) == "BBBBBB"


def test_joining_with_a_valid_code_makes_the_user_member(engine, anna, ben):
    code = db.create_flat(engine, anna, "Rua Augusta 12")
    assert db.join_flat(engine, ben, f" {code.lower()} ") == "Rua Augusta 12"
    assert db.get_membership(engine, ben)["role"] == "member"


def test_joining_with_an_unknown_code_is_rejected(engine, anna, ben):
    db.create_flat(engine, anna, "Rua Augusta 12", make_code=lambda: "AAAAAA")
    with pytest.raises(ValueError):
        db.join_flat(engine, ben, "BBBBBB")
    assert db.get_membership(engine, ben) is None


def test_member_cannot_join_another_flat(engine, anna, ben):
    db.create_flat(engine, anna, "First", make_code=lambda: "AAAAAA")
    db.join_flat(engine, ben, "AAAAAA")
    carl = db.get_or_create_user(engine, "carl@example.com", "Carl")
    db.create_flat(engine, carl, "Second", make_code=lambda: "BBBBBB")
    with pytest.raises(ValueError):
        db.join_flat(engine, ben, "BBBBBB")
    assert db.get_membership(engine, ben)["flat_name"] == "First"


def test_members_see_only_their_own_flat(engine, anna, ben):
    db.create_flat(engine, anna, "First")
    db.create_flat(engine, ben, "Second")
    assert db.list_members(engine, anna) == [{"name": "Anna", "role": "admin"}]
    assert db.list_members(engine, ben) == [{"name": "Ben", "role": "admin"}]


def test_members_are_listed_by_name(engine, anna, ben):
    code = db.create_flat(engine, ben, "Shared")
    db.join_flat(engine, anna, code)
    assert [m["name"] for m in db.list_members(engine, ben)] == ["Anna", "Ben"]
