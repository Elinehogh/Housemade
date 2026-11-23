"""Database tests for the weekly prize. Each test gets a fresh in-memory SQLite database, never the real one."""

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError

import db
from logic import MAX_PRIZES_PER_KIND

MONDAY = date(2026, 11, 23)
TUESDAY = MONDAY + timedelta(days=1)
THURSDAY = MONDAY + timedelta(days=3)
NEXT_MONDAY = MONDAY + timedelta(days=7)
TWO_WEEKS_LATER = MONDAY + timedelta(days=14)


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


def suggest(engine, user, kind="winner", text="A free beer", today=MONDAY):
    return db.add_prize(engine, user, kind, text, today=today)


def score(engine, assigner, user, points, day):
    chore = db.add_chore(engine, assigner, f"Chore {user} {points} {day}", points, user)
    db.tick_off_chore(engine, user, chore, now=datetime.combine(day, datetime.min.time()).replace(hour=12))


# --- Suggesting ------------------------------------------------------------------


def test_new_week_has_no_options(engine, anna):
    data = db.prize_overview(engine, anna, MONDAY)
    assert data["options"] == {"winner": [], "loser": []}
    assert data["chosen"] == {"winner": None, "loser": None}
    assert data["voting_open"] is True


def test_any_member_can_suggest(engine, anna, ben):
    suggest(engine, ben, "loser", "  Cook   dinner on Friday ")
    option = db.prize_overview(engine, anna, MONDAY)["options"]["loser"][0]
    assert (option["name"], option["who"], option["votes"]) == ("Cook dinner on Friday", "Ben", [])


@pytest.mark.parametrize("text", ["   ", "a" * 61])
def test_invalid_suggestion_is_rejected_and_not_saved(engine, anna, text):
    with pytest.raises(ValueError):
        suggest(engine, anna, text=text)
    assert db.prize_overview(engine, anna, MONDAY)["options"]["winner"] == []


def test_duplicate_in_the_same_vote_is_rejected(engine, anna, ben):
    suggest(engine, anna, "winner", "A free beer")
    with pytest.raises(ValueError, match="already"):
        suggest(engine, ben, "winner", "  a FREE beer")


def test_same_text_is_allowed_in_the_other_vote(engine, anna):
    suggest(engine, anna, "winner", "Pizza")
    suggest(engine, anna, "loser", "Pizza")
    data = db.prize_overview(engine, anna, MONDAY)
    assert len(data["options"]["winner"]) == len(data["options"]["loser"]) == 1


def test_same_text_is_allowed_next_week(engine, anna):
    suggest(engine, anna, text="A free beer", today=MONDAY)
    suggest(engine, anna, text="A free beer", today=NEXT_MONDAY)
    assert len(db.prize_overview(engine, anna, NEXT_MONDAY)["options"]["winner"]) == 1


def test_too_many_options_are_rejected(engine, anna):
    for n in range(MAX_PRIZES_PER_KIND):
        suggest(engine, anna, text=f"Prize {n}")
    with pytest.raises(ValueError, match="at most"):
        suggest(engine, anna, text="One too many")


def test_cannot_suggest_after_wednesday(engine, anna):
    with pytest.raises(ValueError, match="closed"):
        suggest(engine, anna, today=THURSDAY)


def test_unknown_kind_is_rejected(engine, anna):
    with pytest.raises(ValueError):
        suggest(engine, anna, kind="runner-up")


def test_user_without_a_flat_is_rejected(engine):
    loner = db.get_or_create_user(engine, "loner@example.com", "Loner")
    with pytest.raises(ValueError):
        suggest(engine, loner)
    with pytest.raises(ValueError):
        db.prize_overview(engine, loner, MONDAY)


# --- Voting ----------------------------------------------------------------------


def test_vote_is_saved_with_the_user_id(engine, anna, ben):
    beer = suggest(engine, anna)
    db.vote_prize(engine, ben, beer, today=TUESDAY)
    votes = db.prize_overview(engine, anna, TUESDAY)["options"]["winner"][0]["votes"]
    assert votes == [{"user_id": ben, "name": "Ben"}]


def test_one_vote_in_each_of_the_two_votes(engine, anna):
    beer = suggest(engine, anna, "winner", "A free beer")
    dinner = suggest(engine, anna, "loser", "Cook dinner")
    db.vote_prize(engine, anna, beer, today=MONDAY)
    db.vote_prize(engine, anna, dinner, today=MONDAY)
    data = db.prize_overview(engine, anna, MONDAY)
    assert len(data["options"]["winner"][0]["votes"]) == len(data["options"]["loser"][0]["votes"]) == 1


def test_second_vote_on_the_same_option_is_rejected(engine, anna):
    beer = suggest(engine, anna)
    db.vote_prize(engine, anna, beer, today=MONDAY)
    with pytest.raises(ValueError, match="already voted"):
        db.vote_prize(engine, anna, beer, today=TUESDAY)


def test_second_vote_on_another_option_in_the_same_vote_is_rejected(engine, anna):
    beer, movie = suggest(engine, anna, text="A free beer"), suggest(engine, anna, text="Picks the movie")
    db.vote_prize(engine, anna, beer, today=MONDAY)
    with pytest.raises(ValueError, match="already voted"):
        db.vote_prize(engine, anna, movie, today=MONDAY)


def test_cannot_vote_after_wednesday(engine, anna):
    beer = suggest(engine, anna)
    with pytest.raises(ValueError, match="closed"):
        db.vote_prize(engine, anna, beer, today=THURSDAY)


def test_cannot_vote_on_last_weeks_option(engine, anna):
    beer = suggest(engine, anna, today=MONDAY)
    with pytest.raises(ValueError, match="this week"):
        db.vote_prize(engine, anna, beer, today=NEXT_MONDAY)


def test_can_vote_again_next_week(engine, anna):
    first = suggest(engine, anna, today=MONDAY)
    db.vote_prize(engine, anna, first, today=MONDAY)
    second = suggest(engine, anna, today=NEXT_MONDAY)
    db.vote_prize(engine, anna, second, today=NEXT_MONDAY)
    assert len(db.prize_overview(engine, anna, NEXT_MONDAY)["options"]["winner"][0]["votes"]) == 1


def test_cannot_vote_on_an_option_that_does_not_exist(engine, anna):
    with pytest.raises(ValueError, match="not on your list"):
        db.vote_prize(engine, anna, 999, today=MONDAY)


def test_database_refuses_a_second_vote_by_itself(engine, anna):
    beer, movie = suggest(engine, anna, text="A free beer"), suggest(engine, anna, text="Picks the movie")
    values = dict(user_id=anna, week_start=MONDAY, kind="winner")
    with engine.begin() as conn:
        conn.execute(insert(db.weekly_prize_votes).values(prize_id=beer, **values))
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(insert(db.weekly_prize_votes).values(prize_id=movie, **values))


# --- The deal --------------------------------------------------------------------


def test_most_votes_is_chosen_and_listed_first(engine, anna, ben, cleo):
    beer, movie = suggest(engine, anna, text="A free beer"), suggest(engine, anna, text="Picks the movie")
    db.vote_prize(engine, anna, beer, today=MONDAY)
    db.vote_prize(engine, ben, movie, today=MONDAY)
    db.vote_prize(engine, cleo, movie, today=MONDAY)
    data = db.prize_overview(engine, anna, THURSDAY)
    assert data["voting_open"] is False
    assert data["chosen"]["winner"]["name"] == "Picks the movie"
    assert [option["name"] for option in data["options"]["winner"]] == ["Picks the movie", "A free beer"]


def test_tie_goes_to_the_first_suggested(engine, anna, ben):
    beer, movie = suggest(engine, anna, text="A free beer"), suggest(engine, anna, text="Picks the movie")
    db.vote_prize(engine, anna, movie, today=MONDAY)
    db.vote_prize(engine, ben, beer, today=MONDAY)
    assert db.prize_overview(engine, anna, THURSDAY)["chosen"]["winner"]["name"] == "A free beer"


def test_no_votes_means_no_deal(engine, anna):
    suggest(engine, anna)
    assert db.prize_overview(engine, anna, THURSDAY)["chosen"]["winner"] is None


# --- Last week's result ----------------------------------------------------------


def test_last_week_shows_who_won_and_lost_and_the_deal(engine, anna, ben, cleo):
    beer = suggest(engine, anna, "winner", "A free beer")
    dinner = suggest(engine, anna, "loser", "Cook dinner on Friday")
    db.vote_prize(engine, ben, beer, today=MONDAY)
    db.vote_prize(engine, ben, dinner, today=MONDAY)
    score(engine, anna, anna, 8, TUESDAY)
    score(engine, anna, ben, 5, TUESDAY)
    score(engine, anna, cleo, 2, TUESDAY)
    assert db.prize_overview(engine, anna, NEXT_MONDAY)["last_week"] == {
        "winners": ["Anna"], "losers": ["Cleo"],
        "winner_prize": "A free beer", "loser_prize": "Cook dinner on Friday",
    }


def test_points_from_this_week_do_not_count_for_last_week(engine, anna, ben):
    score(engine, anna, anna, 5, MONDAY)
    score(engine, anna, ben, 9, NEXT_MONDAY)
    last = db.prize_overview(engine, anna, NEXT_MONDAY)["last_week"]
    assert (last["winners"], last["losers"]) == (["Anna"], ["Ben"])


def test_points_from_two_weeks_ago_do_not_count(engine, anna, ben):
    score(engine, anna, anna, 5, MONDAY)
    last = db.prize_overview(engine, anna, TWO_WEEKS_LATER)["last_week"]
    assert (last["winners"], last["losers"]) == ([], [])


def test_everyone_equal_last_week_has_no_winner_or_loser(engine, anna, ben):
    score(engine, anna, anna, 3, TUESDAY)
    score(engine, anna, ben, 3, TUESDAY)
    last = db.prize_overview(engine, anna, NEXT_MONDAY)["last_week"]
    assert (last["winners"], last["losers"]) == ([], [])


# --- Another flat ----------------------------------------------------------------


def test_another_flat_does_not_see_the_options_or_result(engine, anna, ben, carl):
    beer = suggest(engine, anna)
    db.vote_prize(engine, anna, beer, today=MONDAY)
    score(engine, anna, anna, 5, MONDAY)
    assert db.prize_overview(engine, carl, MONDAY)["options"] == {"winner": [], "loser": []}
    last = db.prize_overview(engine, carl, NEXT_MONDAY)["last_week"]
    assert last == {"winners": [], "losers": [], "winner_prize": None, "loser_prize": None}


def test_another_flat_cannot_vote(engine, anna, carl):
    beer = suggest(engine, anna)
    with pytest.raises(ValueError, match="not on your list"):
        db.vote_prize(engine, carl, beer, today=MONDAY)
    assert db.prize_overview(engine, anna, MONDAY)["options"]["winner"][0]["votes"] == []


def test_two_flats_can_suggest_the_same_prize(engine, anna, carl):
    suggest(engine, anna)
    suggest(engine, carl)
    assert len(db.prize_overview(engine, anna, MONDAY)["options"]["winner"]) == 1
    assert len(db.prize_overview(engine, carl, MONDAY)["options"]["winner"]) == 1
