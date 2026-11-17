# Team plan

How we split the work on Housemade. Agreed by the team on 17 November 2026.

## 1. Who builds what

| Person | Tab | What to build |
|---|---|---|
| A | 🧹 Chores | Chores saved in the database, ticking off a chore gives points, and a leaderboard |
| B | 🛒 Shopping | Shopping list, and costs split equally (`balances` already exists in `logic.py`) |
| C | 🫙 Fund | Pant money in, costs out, a savings goal, and a rule that the fund can never go below zero |
| D | 🎉 Activities | Suggestions, voting, an "can we afford it" filter, and maybe a weather API |
| E | Shared | Google login, roles (admin), README, and owner of the tables in `db.py` |

If we are fewer than five, one person also takes one of the tabs.

## 2. Steps for each person, in this order

1. Make a branch in GitHub Desktop, for example `feature/chores`.
2. Write a short spec in `specs/<feature>.md` (for example `specs/chores.md`) with
   four headings: Why, What, Out of scope and Done when.
3. Write the rules in `logic.py` and the tests in `tests/` first. Test both what
   should be accepted and what should be rejected.
4. Tell person E which table you need. Person E adds it to `db.py`, so we do not
   get merge conflicts.
5. Replace the sample data in your own file in `screens/` with real data from
   the database.
6. Run `uv run pytest`, open a pull request, and get someone else in the group
   to review it before merging.
