# Design and overview

## Why

The app is used every day by everyone in a flat, so it should feel friendly
and calm, and show what matters to you right away: what you have to do, what
you owe, and how the fund is doing. Before login, a new visitor should
understand what Housemade is in a few seconds.

## What

- A calm sea-blue theme: petrol-blue buttons and highlights on a light
  blue-grey background, with deep blue text. A matching dark theme is used when the visitor's device
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
- Every member has an avatar: an emoji (from a fixed list of 16) on a
  coloured background (from a fixed list of 7 colours). Right after their
  first login, before creating or joining a flat, a member picks their
  avatar. They can change it later from the top of the Flat tab, or from the sidebar.
- The avatar is shown next to the member's name in the sidebar, the member
  list, the chores leaderboard and who owes what. A member who has not picked
  one gets a neutral default.
- Only emojis and colours from the lists are accepted, so nothing a member
  types ends up in the page as code.

## Out of scope

- Choosing a theme inside the app (it follows the device).
- Uploaded pictures or animations.
- Google profile pictures (we only use the name and email from Google).
- Changing the Activities tab (it is being moved to the database).

## Done when

- The overview numbers come from a pure function in `logic.py`, with tests:
  open and overdue chores, points this week (not last week, not other
  members), and no chores at all.
- `money_overview` also returns the member's own balance, with a test.
- Tests cover picking an avatar, rejecting an emoji or colour that is not on
  the lists, the default avatar, members seeing only their own flat's
  avatars, and adding the avatar columns to an existing database.
- The app looks right in light and dark mode, before and after login.
- `uv run pytest` passes.
