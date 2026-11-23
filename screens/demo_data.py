"""Sample data for the preview. Kept per visitor in st.session_state, never saved.

Each feature replaces its part of this with real data from db.py when it is built.
"""

from datetime import date, timedelta

import streamlit as st

from logic import week_start

MEMBERS = ["You", "Ana", "Tom", "Sara"]


def init() -> None:
    """Fill the session with sample data the first time a visitor opens the app."""
    if "demo" in st.session_state:
        return

    def days_ago(n: int) -> date:
        return date.today() - timedelta(days=n)

    monday = week_start(date.today())
    last_monday = monday - timedelta(days=7)

    st.session_state.demo = {
        "chores": [
            {"chore": "Dishes", "who": "You", "points": 2, "done": False},
            {"chore": "Take out trash", "who": "Ana", "points": 1, "done": True},
            {"chore": "Clean bathroom", "who": "Tom", "points": 5, "done": False},
            {"chore": "Vacuum living room", "who": "Sara", "points": 3, "done": True},
        ],
        "points": {"You": 12, "Ana": 15, "Tom": 8, "Sara": 10},
        "shopping": [
            {"item": "Toilet paper", "bought": False},
            {"item": "Dish soap", "bought": False},
            {"item": "Milk", "bought": True},
        ],
        "payments": [("Ana", 18.40), ("You", 7.20), ("Tom", 32.00)],
        "fund": [
            {"what": "Deposit from party bottles", "who": "Sara", "amount": 6.40},
            {"what": "Deposit money", "who": "You", "amount": 3.10},
            {"what": "Pizza night", "who": "Tom", "amount": -12.00},
            {"what": "Deposit money", "who": "Ana", "amount": 4.50},
        ],
        "fund_goal": ("Flat trip to Sintra", 80.0),
        "last_week_points": {"You": 9, "Ana": 14, "Tom": 6, "Sara": 11},
        "prizes": [
            {"id": 1, "week": last_monday, "kind": "winner", "name": "Picks the weekend plan", "who": "Ana",
             "votes": ["Ana", "Sara", "You"]},
            {"id": 2, "week": last_monday, "kind": "loser", "name": "Buy the next round", "who": "Sara",
             "votes": ["Ana", "Sara"]},
            {"id": 3, "week": monday, "kind": "winner", "name": "A free beer from each flatmate", "who": "Ana",
             "votes": ["Ana", "Tom"]},
            {"id": 4, "week": monday, "kind": "winner", "name": "Picks the next movie", "who": "Sara",
             "votes": ["Sara"]},
            {"id": 5, "week": monday, "kind": "loser", "name": "Cook dinner on Friday", "who": "Tom",
             "votes": ["Tom", "Sara"]},
            {"id": 6, "week": monday, "kind": "loser", "name": "Clean the bathroom next week", "who": "Ana",
             "votes": ["Ana"]},
        ],
        "house_rules": [
            {"id": 1, "text": "Quiet after 23:00 on weekdays", "who": "Ana", "added": days_ago(30), "voters": []},
            {"id": 2, "text": "Clean the kitchen right after you cook", "who": "Tom", "added": days_ago(21), "voters": ["Ana"]},
            {"id": 3, "text": "No shoes in the living room", "who": "Sara", "added": days_ago(7), "voters": ["Tom", "Ana"]},
        ],
        "activities": [
            {"id": 1, "activity": "Pizza & movie night", "cost_cents": 2500, "planned_on": days_ago(-3),
             "added_by": "Tom", "who": "Tom"},
            {"id": 2, "activity": "Picnic in Parque Eduardo VII", "cost_cents": 1500, "planned_on": days_ago(-5),
             "added_by": "Ana", "who": "Ana"},
            {"id": 3, "activity": "Day trip to Sintra", "cost_cents": 8000, "planned_on": days_ago(-12),
             "added_by": "Sara", "who": "Sara"},
            {"id": 4, "activity": "Board game evening", "cost_cents": 0, "planned_on": days_ago(-1),
             "added_by": "You", "who": "You"},
        ],
        # Each member votes at most once a day, and once per activity (see logic.check_can_vote).
        "votes": [
            {"activity": "Picnic in Parque Eduardo VII", "who": "Tom", "day": days_ago(3)},
            {"activity": "Picnic in Parque Eduardo VII", "who": "Ana", "day": days_ago(2)},
            {"activity": "Pizza & movie night", "who": "Tom", "day": days_ago(2)},
            {"activity": "Board game evening", "who": "Sara", "day": days_ago(2)},
            {"activity": "Pizza & movie night", "who": "Ana", "day": days_ago(1)},
            {"activity": "Picnic in Parque Eduardo VII", "who": "Sara", "day": days_ago(1)},
            {"activity": "Day trip to Sintra", "who": "Tom", "day": days_ago(0)},
        ],
    }
