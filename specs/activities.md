# Activities in the database

## Why

Activities only help a flat decide if everyone sees the same list. Until now
the list and the votes were sample data, so each visitor had their own copy.
Saving them makes voting real, and lets the flat plan its own things and check
them against the real fund.

## What

- Activities and votes are saved in the database. Each member only sees and
  changes the activities of their own flat.
- Any member can add an activity with a name, a price for the whole flat and a
  date.
  - A name is 1 to 40 characters. Extra spaces are removed.
  - A flat cannot have the same activity twice (capital letters do not matter).
    Two different flats can have the same activity.
  - A price is €0 (free) to €1000, with at most 2 decimals.
  - The date cannot be in the past.
- Adding one of today's weather ideas saves it with its price and today's date.
- A member can vote once per activity and once per day, as in
  `specs/activity-voting.md`. Votes belong to the member's user id, not their
  name. The database itself also refuses a second vote on the same activity or
  on the same day, so two clicks at the same moment cannot both count.
- The person who added an activity and the flat's admin can remove it. They
  are asked to confirm first. Its votes are removed with it, so anyone who
  voted for it today can vote again today.
- "Only what the fund can pay for" uses the real balance from the Fund tab.
  Free activities are always affordable.
- The list refreshes itself like the other shared lists
  (`specs/live-updates.md`). The add form stays outside the refreshing part.
- The preview without a login keeps working with sample data.

## Out of scope

- Editing an activity.
- Taking back a vote.
- Paying for an activity from the fund.
- Removing or archiving activities automatically after their date.

## Done when

- The rules are pure functions in `logic.py`, and all saving is in `db.py`.
- The owner of the tables in `db.py` has agreed to the two new tables before
  this is merged.
- Tests cover adding (tidied, empty, too long, duplicate, price and date
  limits), voting (accepted, twice on one activity, twice on one day, the next
  day, an activity that does not exist), the database refusing duplicate votes
  by itself, removing (by the person who added it, by the admin, by someone
  else), and another flat not seeing, voting on or removing the list.
- `uv run pytest` passes.
