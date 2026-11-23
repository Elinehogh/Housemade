# Speed

## Why

The app runs in the United States and the database is in Frankfurt, so every
trip to the database takes a noticeable moment. The Today tab made 33 queries
over 30 connections for one click, which made the whole app feel slow.

## What

- The Today tab loads everything it shows in one visit to the database: one
  connection and at most 7 queries, however much data the flat has.
- The top of every page looks up the member's avatar, flat and role in one
  query. Their user id is looked up once per visit.
- Together, one click on Today makes fewer than 10 trips to the database.
- The Today tab shows the same numbers as before, and still refreshes itself
  every 15 seconds (`specs/live-updates.md`).
- Each member still only reaches their own flat's data.

## Out of scope

- Moving the app or the database to another host or region.
- Caching data between clicks, which could show flatmates old information.
- Speeding up the other tabs.

## Done when

- Tests check that the Today data matches what the separate database functions
  return, including an empty flat.
- Tests check that it uses one connection and at most 7 queries, also when the
  flat has more data.
- Tests check that a member never gets another flat's data, and that someone
  without a flat is rejected.
- `uv run pytest` passes.
