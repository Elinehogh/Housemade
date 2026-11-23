"""Tests for the numbers on the Flat tab overview (specs/design.md)."""

from datetime import date, datetime

from logic import my_chores_summary

ME, OTHER = 1, 2
WEDNESDAY = date(2026, 11, 18)
THIS_WEEK = datetime(2026, 11, 17, 10, 0)
LAST_WEEK = datetime(2026, 11, 15, 10, 0)


def chore(who, points=1, done_at=None, due_on=None, name="Chore"):
    return {"name": name, "assigned_to": who, "points": points, "done_at": done_at,
            "done": done_at is not None, "due_on": due_on}


def test_no_chores_gives_zeros():
    assert my_chores_summary([], ME, WEDNESDAY) == {"open": 0, "overdue": 0, "points": 0, "next": []}


def test_open_and_overdue_chores_are_counted():
    chores = [
        chore(ME, due_on=date(2026, 11, 17)),  # overdue
        chore(ME, due_on=WEDNESDAY),  # due today, not overdue
        chore(ME),  # no deadline
        chore(OTHER, due_on=date(2026, 11, 1)),  # someone else's
    ]
    summary = my_chores_summary(chores, ME, WEDNESDAY)
    assert (summary["open"], summary["overdue"]) == (3, 1)


def test_points_count_only_my_chores_done_this_week():
    chores = [
        chore(ME, points=3, done_at=THIS_WEEK),
        chore(ME, points=5, done_at=LAST_WEEK),
        chore(OTHER, points=4, done_at=THIS_WEEK),
        chore(ME, points=2),  # not done yet
    ]
    assert my_chores_summary(chores, ME, WEDNESDAY)["points"] == 3


def test_next_chores_are_mine_soonest_first_and_at_most_three():
    chores = [
        chore(ME, name="No deadline"),
        chore(ME, name="Friday", due_on=date(2026, 11, 20)),
        chore(ME, name="Thursday", due_on=date(2026, 11, 19)),
        chore(ME, name="Saturday", due_on=date(2026, 11, 21)),
        chore(OTHER, name="Not mine", due_on=date(2026, 11, 18)),
        chore(ME, name="Done", due_on=date(2026, 11, 18), done_at=THIS_WEEK),
    ]
    names = [c["name"] for c in my_chores_summary(chores, ME, WEDNESDAY)["next"]]
    assert names == ["Thursday", "Friday", "Saturday"]
