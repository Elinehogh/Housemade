# Design and overview

## Why

The app is used every day by everyone in a flat, so it should feel friendly
and calm, and show what matters to you right away: what you have to do, what
you owe, and how the fund is doing. Before login, a new visitor should
understand what Housemade is in a few seconds.

## What

- A warm theme: coral buttons and highlights on a cream background, with
  dark slate text. A matching dark theme is used when the visitor's device
  is in dark mode. Text and buttons are easy to read in both.
- Before login, a short welcome page explains the app with three cards
  (chores, shopping and costs, the shared fund) above the Google login
  button, and links to the privacy policy.
- The Flat tab is an overview for the logged-in member:
  - their open chores, and how many are overdue,
  - their points this week,
  - what they should get back or owe for shared costs,
  - how much is in the fund, and the progress towards the goal,
  - their next chores (up to 3, soonest deadline first),
  - the invite code (for the admin) and the members of the flat.
- The page header shows the app name and the flat's name once, and the
  sidebar shows who is logged in and which flat they are in.
- The preview with sample data shows the same overview from the sample data.

## Out of scope

- Choosing a theme inside the app (it follows the device).
- Custom pictures, animations or avatars.
- Changing the Activities tab (it is being moved to the database).

## Done when

- The overview numbers come from a pure function in `logic.py`, with tests:
  open and overdue chores, points this week (not last week, not other
  members), and no chores at all.
- `money_overview` also returns the member's own balance, with a test.
- The app looks right in light and dark mode, before and after login.
- `uv run pytest` passes.
