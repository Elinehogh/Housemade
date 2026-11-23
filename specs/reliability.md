# Reliability

## Why

Housemade depends on a weather service, a location service and a hosted
database. When one of them is slow or down, the app should stay usable and say
what is going on, instead of freezing or showing a technical error.

## What

- The weather and location services get at most 2 seconds per step. If one
  fails, the app does not ask it again for 2 minutes, so clicks stay fast. The
  location falls back to Lisbon, and Today works without the weather tile.
- The app stops trying to connect to the database after 5 seconds.
- If the database cannot be reached, the page shows a short, friendly message
  with a **Try again** button. Parts that refresh by themselves show the message
  and try again on the next refresh. The real error is still written to the log.
- Only connection problems get this message. Other errors are not hidden.
- Deposit money from bottles and cans is called "deposit money" on screen.
  Entries saved earlier as "Pant" are shown the same way.
- `uv run streamlit run app.py` and `uv run pytest` work on Intel and Apple
  Silicon Macs, and GitHub Codespaces uses the project's Python and packages.

## Out of scope

- Saving changes while the database is down.
- Automatic alerts when a service is down.

## Done when

- Tests cover a working service, a failed service not being asked again, trying
  again after the wait, one failed service not blocking the other, connection
  errors getting the message, and other errors not being hidden.
- `uv run pytest` passes.
