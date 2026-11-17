# Working rules for coding agents

Housemade is a web app for shared flats: chores, a shared shopping list,
a shared fund (including deposit money from bottles and cans) and activities
to do together. Team project for Introduction to Programming, Nova SBE 2026/27.

## Commands

- Run the app: `uv run streamlit run app.py`
- Run the tests: `uv run pytest`

## Folder structure

- `app.py`: screens (Streamlit). No rules here, only showing and asking.
- `logic.py`: rules as pure functions. No Streamlit, no database.
- `db.py`: all reading and writing of saved data.
- `services.py`: calls to outside services (location, weather).
- `config.py`: app name and shared settings.
- `tests/`: pytest tests, mainly for `logic.py`.
- `specs/`: one spec per feature (Why, What, Out of scope, Done when).
- `docs/`: background documents for the product.

## Storage

- The deployed app uses a hosted Postgres database on Supabase. Its
  connection string is a secret, read from Streamlit secrets; never write it
  in code or commit it.
- Without that secret (tests, local runs) the app uses SQLite.
- All database code lives in `db.py` and goes through SQLAlchemy, so the same
  functions work on SQLite and Postgres.
- Tests use a fresh in-memory SQLite database (`sqlite://`), never the real one.
- Access control: functions that touch a flat's data take the user's id and
  look up their own flat. Never accept a flat id from the screen.
- One person owns changes to the tables in `db.py`. Agree with them before
  adding or changing a table.

## Rules

- Work on a branch, never directly on `main`. Merge through a pull request.
- Before implementing, read the spec in `specs/` and propose tests first.
- Test both accepted and rejected actions, and edge cases.
- Never weaken, skip or delete a test to make it pass. Fix a wrong test
  explicitly against the spec.
- Run `uv run pytest` and show the output before saying you are done.
- The repository is public: never commit keys, passwords or database files.
  Secrets go in `.streamlit/secrets.toml` locally (ignored by git) and in the
  hosting service's secrets settings.
- Keep dependencies few and pinned to exact versions in `pyproject.toml`.
