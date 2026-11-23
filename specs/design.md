# Design and overview

## Why

The app is used every day by everyone in a flat, so it should feel friendly
and calm, and show what matters to you right away: what you have to do, what
you owe, and how the fund is doing. Before login, a new visitor should
understand what Housemade is in a few seconds.

## What

- The Sky look: big, flat colour tiles (cobalt, yellow, coral, mint and lilac)
  with bold titles, on a white background. A matching dark theme is used when
  the visitor's device or Streamlit's settings are in dark mode. Text and
  buttons are easy to read in both.
- Before login, a short welcome page explains the app with three cards
  (chores, shopping and costs, the shared fund) above the Google login
  button, and links to the privacy policy.
- The first tab, Today, is an overview for the logged-in member:
  - first, what is waiting for their vote (`specs/votes-waiting.md`),
  - a large weather tile for where they are, with ideas for today's weather
    that can be added to the activities,
  - their next chore (soonest deadline first), with a button to finish it,
    and how many other chores and overdue chores they have,
  - what they owe or get back for shared costs, and from or to whom,
  - how much is in the fund, and the progress towards the goal,
  - what is on the shopping list,
  - the points of everyone in the flat this week,
  - the activity with the most votes,
  - a House rules tile that only shows its title and opens the House rules tab,
  - the invite code (for the admin) and the members of the flat.
- The page header shows the app name and the flat's name once, and the
  sidebar shows who is logged in and which flat they are in.
- The preview with sample data shows the same overview from the sample data.
- Every member has an avatar: an emoji (from a fixed list of 16) on a
  coloured background (from a fixed list of 7 colours). Right after their
  first login, before creating or joining a flat, a member picks their
  avatar. They can change it later from the top of the Today tab, or from the sidebar.
- The avatar is shown next to the member's name in the sidebar, the member
  list, the chores leaderboard and who owes what. A member who has not picked
  one gets a neutral default.
- Only emojis and colours from the lists are accepted, so nothing a member
  types ends up in the page as code.

## Out of scope

- Choosing a theme inside the app (it follows the device).
- Uploaded pictures or animations.
- Google profile pictures (we only use the name and email from Google).

## Done when

- The overview numbers come from a pure function in `logic.py`, with tests:
  open and overdue chores, points this week (not last week, not other
  members), and no chores at all.
- The text on the tiles comes from pure functions, with tests: the weather
  headline, owing, getting back or being even, who to pay, and a short
  shopping list.
- `money_overview` also returns the member's own balance and who they pay or get money from, with tests.
- Tests cover picking an avatar, rejecting an emoji or colour that is not on
  the lists, the default avatar, members seeing only their own flat's
  avatars, and adding the avatar columns to an existing database.
- The app looks right in light and dark mode, before and after login.
- `uv run pytest` passes.
