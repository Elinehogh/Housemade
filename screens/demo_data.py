"""Sample data for the preview. Kept per visitor in st.session_state, never saved.

Each feature replaces its part of this with real data from db.py when it is built.
"""

from datetime import date, timedelta

import streamlit as st

MEMBERS = ["You", "Ana", "Tom", "Sara"]


def init() -> None:
    """Fill the session with sample data the first time a visitor opens the app."""
    if "demo" in st.session_state:
        return

    def days_ago(n: int) -> date:
        return date.today() - timedelta(days=n)

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
            {"what": "Pant from party bottles", "who": "Sara", "amount": 6.40},
            {"what": "Pant", "who": "You", "amount": 3.10},
            {"what": "Pizza night", "who": "Tom", "amount": -12.00},
            {"what": "Pant", "who": "Ana", "amount": 4.50},
        ],
        "fund_goal": ("Flat trip to Sintra", 80.0),
        "activities": [
            {"activity": "Pizza & movie night", "cost": 25},
            {"activity": "Picnic in Parque Eduardo VII", "cost": 15},
            {"activity": "Day trip to Sintra", "cost": 80},
            {"activity": "Board game evening", "cost": 0},
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
