"""Activities the flat can do together, voting, and what the fund can pay for."""

import streamlit as st


def show() -> None:
    demo = st.session_state.demo
    fund = sum(entry["amount"] for entry in demo["fund"])

    st.subheader("🎉 Things to do together")
    st.caption("Coming later: suggestions based on the weather and who is free.")
    only_affordable = st.toggle(f"Only what the fund can pay for (€{fund:.2f})")

    activities = sorted(demo["activities"], key=lambda a: a["votes"], reverse=True)
    for i, activity in enumerate(activities):
        if only_affordable and activity["cost"] > fund:
            continue
        cost = "free" if activity["cost"] == 0 else f"€{activity['cost']}"
        left, right = st.columns([4, 1])
        left.write(f"**{activity['activity']}** · {cost} · {activity['votes']} votes")
        if right.button("👍 Vote", key=f"vote_{i}"):
            activity["votes"] += 1
            st.rerun()
