# Live updates

## Why

A flat is shared. When one flatmate adds a chore or ticks one off, the others
should see it without reloading the page, or the leaderboard and the list are
out of date and people do the same chore twice.

## What

- Every part of a screen that shows data from the database asks the database
  again every 15 seconds and redraws itself. Today that is:
  - the tiles and the members of the flat (Today tab),
  - the list of chores and the leaderboard (Chores tab),
  - the list of activities and their votes (Activities tab).
- Only that part is redrawn, not the whole page, so the open tab and the
  scroll position stay where they are.
- Forms are not inside the parts that refresh, so a half-typed chore is not
  lost.
- The interval is `REFRESH_SECONDS` in `config.py`.
- The preview with sample data does not refresh: its data is kept per visitor
  and nobody else can change it.
- The Shopping and Fund tabs are saved in the database, but do not refresh
  themselves yet.

## Out of scope

- Instant updates pushed from the server (the app asks every 15 seconds
  instead).
- Showing who changed what, or notifications.

## Done when

- With two browser windows logged in to the same flat, a chore added or
  ticked off in one window shows up in the other within 15 seconds, without
  reloading.
- `uv run pytest` passes.
