# Chores

## Why

Chores are the most common fight in a shared flat. Housemade makes it clear
who does what, and rewards the people who do their part with points. Each
week the flat votes on what the winner gets and what the loser has to do
(`specs/weekly-prize.md`).

## What

- Any member can add a chore to their own flat: a name, how many points it is
  worth, and which member of the flat should do it.
- A chore name is 1 to 40 characters. Extra spaces are removed.
- To add a chore, members can pick a common one from a list (clean the
  bathroom, vacuum, take out the trash and more) or type their own. A common
  chore comes with suggested points, for example 5 for the bathroom and 1 for
  the trash, which the member can change before adding it. A chore they type
  themselves starts at 2 points.
- A chore is worth 1 to 10 points (whole numbers).
- A chore can only be given to a member of the same flat.
- Only the person a chore is given to can tick it off.
- A chore can only be ticked off once.
- A chore can have a deadline (a date), or no deadline. A deadline cannot be
  in the past when the chore is added.
- Open chores are listed by deadline, soonest first, and chores without a
  deadline come last. A chore past its deadline is marked overdue, and one
  due today is marked as due today.
- A member can also log a chore they have just done ("I took out the
  trash"). It is saved as done right away, given to themselves, and counts
  for the leaderboard. You can only log chores you did yourself.
- A done chore shows when it was done. Chores done before this week (Monday)
  are moved to a history list, so the list starts fresh every week.
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
- Fewer points for chores done after the deadline.
- Checking that a logged chore was really done: flatmates trust each other.

## Done when

- Chores are saved in the database, not in the sample data.
- Every common chore has a valid name and suggested points from 1 to 10.
- Tests cover adding, ticking off and the leaderboard, both accepted and
  rejected actions: an empty or too long name, 0 or 11 points, a person from
  another flat, ticking off someone else's chore, ticking off twice, and a
  chore from another flat, a deadline in the past, no deadline, logging a
  chore for someone else, and the order of the list.
- The deadline column is added to the existing database without losing
  chores.
- `uv run pytest` passes.
- It works on https://housemade.streamlit.app/, not only locally.
