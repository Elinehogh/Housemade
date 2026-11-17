# Chores

## Why

Chores are the most common fight in a shared flat. Housemade makes it clear
who does what, and rewards the people who do their part with points. This
week's winner picks the next flat activity, which ties chores to the fund and
the activities.

## What

- Any member can add a chore to their own flat: a name, how many points it is
  worth, and which member of the flat should do it.
- A chore name is 1 to 40 characters. Extra spaces are removed.
- A chore is worth 1 to 10 points (whole numbers).
- A chore can only be given to a member of the same flat.
- Only the person a chore is given to can tick it off.
- A chore can only be ticked off once.
- The leaderboard shows every member of the flat with their points this week
  (from Monday), highest first. Members with the same points are sorted by
  name. Members with no points are shown with 0.
- Everything is saved in the database, and each member only sees and changes
  chores in their own flat.

## Out of scope

- Repeating chores (for example "dishes every day").
- Rotating chores automatically between members.
- Editing or deleting a chore.
- Reminders or notifications.

## Done when

- Chores are saved in the database, not in the sample data.
- Tests cover adding, ticking off and the leaderboard, both accepted and
  rejected actions: an empty or too long name, 0 or 11 points, a person from
  another flat, ticking off someone else's chore, ticking off twice, and a
  chore from another flat.
- `uv run pytest` passes.
- It works on https://housemade.streamlit.app/, not only locally.
