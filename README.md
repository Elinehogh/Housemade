# Housemade

Chores, shopping and a shared fund for your flat.

**Deployed app:** https://housemade.streamlit.app

**Privacy policy:** [PRIVACY.md](PRIVACY.md)

Housemade is a web app for people who share a flat. It keeps track of who
cleans what, what needs to be bought, who paid for shared things, the money in
the shared fund (including deposit money from bottles and cans), and what the
flat wants to do together. Team project for Introduction to Programming,
Nova SBE 2026/27.

## Team

| Name | Student number |
|---|---|
| Eline Høgh | 80926 |
| Emil Rydin | 78032 |
| August Setlo | 78469 |

## Objectives

Living together goes better when everyone can see what is going on. Housemade
aims to:

- make chores fair and visible, with points and a weekly leaderboard,
- keep one shopping list that the whole flat can see and tick off,
- split shared costs fairly and show who owes whom,
- collect small amounts, such as bottle deposits, in a shared fund towards a goal,
- help the flat decide what to do together, by voting.

## What the app does

- **Log in with Google**, then create a flat or join one with an invite code.
  Every member picks an avatar (an emoji on a colour).
- **Today:** an overview with your next chore, what you owe or get back, the
  fund, the shopping list, this week's points, the weather with activity
  ideas, and anything waiting for your vote.
- **Chores:** pick common chores from a list or type your own, with points and
  an optional deadline. Log a chore you just did. Weekly leaderboard, history
  and a weekly prize the flat votes on.
- **Shopping:** a shared list with common items to pick from. Add what you
  paid for the flat; the cost is split equally and the app shows who should
  pay whom. Only the person who got the money can confirm a payment back.
- **Fund:** add deposit money and other income, the admin records what is
  paid out, set a goal and download the entries as CSV.
- **Activities:** suggest things to do together, get ideas based on today's
  weather where you are, and vote (once per activity, once a day).
- **House rules:** add rules for the flat; a majority vote removes one.
- Shared data refreshes by itself every 15 seconds, and the app works in
  light and dark mode and on a phone.

## Install and run

You need [uv](https://docs.astral.sh/uv/getting-started/installation/), which
installs the right Python version (3.12) and all packages by itself.

```
git clone https://github.com/Elinehogh/Housemade.git
cd Housemade
uv run streamlit run app.py
```

The app opens at http://localhost:8501. Stop it with Ctrl + C.

**Without any setup, the app runs as a preview with sample data.** All tabs
work, but nothing is saved. This is the quickest way to try it.

### With login and saved data (optional)

1. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`.
2. Fill in a Google OAuth client (from Google Cloud Console) under `[auth]`.
3. Leave out `DATABASE_URL` to save data in a local SQLite file
   (`housemade.db`), or set it to a Postgres connection string.

`secrets.toml` is ignored by git. The deployed app keeps the same values in
Streamlit Community Cloud's secrets settings and uses a Postgres database on
Supabase (EU).

## Tests

```
uv run pytest
```

The tests cover the rules in `logic.py` and the database functions in `db.py`,
including actions that should be rejected (for example confirming a payment
someone else received, or seeing another flat's data). They use a fresh
in-memory SQLite database, never the real one.

## Project structure

| Path | What it holds |
|---|---|
| `app.py` | The page: login, creating or joining a flat, and the tabs |
| `screens/` | One file per tab or part of the screen (Streamlit only) |
| `logic.py` | The rules as pure functions, with no Streamlit or database |
| `db.py` | All reading and writing of saved data (SQLAlchemy: SQLite or Postgres) |
| `services.py` | Calls to outside services: location (ipinfo.io) and weather (Open-Meteo) |
| `config.py` | App name and shared settings |
| `specs/` | One spec per feature: why, what, out of scope, done when |
| `tests/` | pytest tests |
| `AGENTS.md` | Working rules for the team and the coding assistants we used |

Built with Python 3.12, Streamlit, SQLAlchemy, Authlib and pytest. Dependencies
are pinned to exact versions in `pyproject.toml` and `uv.lock`.

## How we worked

- Each feature started as a spec in `specs/`, then tests, then the code.
- Every change was made on its own branch and merged into `main` through a
  pull request.
- Rough split of the work (see the commit history and pull requests for details):
  - **Eline:** project setup, database layer, Google login and flats, shopping
    and shared costs, common chores and deadlines, design (welcome page,
    avatars) and the privacy policy.
  - **Emil:** activities in the database, weather-based ideas and voting,
    live updates, the Today tab and the Sky design, house rules, the weekly
    prize and speed.
  - **August:** the team plan, chores in the database with points and the
    leaderboard, and the shared fund with goal and CSV export.
- We used AI coding assistants (Claude) to help write code and tests, following
  the rules in `AGENTS.md`.
