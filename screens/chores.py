"""Chores: who does what this week, ticking off, and the points leaderboard."""

import streamlit as st


def show() -> None:
    demo = st.session_state.demo
    st.subheader("🧹 Chores this week")

    for i, chore in enumerate(demo["chores"]):
        label = f"{chore['chore']} · {chore['who']} · {chore['points']} pts"
        done = st.checkbox(label, value=chore["done"], key=f"chore_{i}", disabled=chore["done"])
        if done and not chore["done"]:
            chore["done"] = True
            demo["points"][chore["who"]] += chore["points"]
            st.rerun()

    st.subheader("🏆 Leaderboard")
    ranking = sorted(demo["points"].items(), key=lambda item: item[1], reverse=True)
    for place, (name, points) in enumerate(ranking, start=1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(place, "  ")
        st.write(f"{medal} **{name}**: {points} points")
    st.caption("This week's winner picks the next flat activity.")
