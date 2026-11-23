# Weekly prize

## Why

Points are more fun when something is at stake. Each week the flat decides
together what the winner of the leaderboard gets and what the loser has to do,
for example a free beer from each flatmate, or cooking dinner on Friday.

## What

- Under the leaderboard, each week has two votes: **Winner gets** and **Loser
  has to**. A week runs from Monday to Sunday, like the leaderboard.
- From Monday to Wednesday, any member can suggest an option for either vote.
  - A suggestion is 1 to 60 characters. Extra spaces are removed.
  - The same suggestion cannot be made twice in the same vote that week
    (capital letters do not matter).
  - Each vote can have at most 5 options a week.
  - The form offers common ideas, and members can type their own.
- From Monday to Wednesday, each member has one vote in each of the two votes.
  A vote cannot be taken back. The database itself also refuses a second vote.
- Voting closes at the end of Wednesday, so nobody votes knowing who is about
  to lose. From Thursday the option with the most votes is the week's deal.
  - If options tie, the one suggested first wins.
  - If nobody voted, that week has no deal for that vote.
- The next week shows last week's result: who won and what they get, and who
  lost and what they have to do.
  - People with the same top or bottom points share the result.
  - If everyone has the same points, there is no winner or loser.
- Each member only sees and votes on their own flat's prizes.
- The prizes refresh themselves like the other shared lists
  (`specs/live-updates.md`). The suggestion forms stay outside the refreshing
  part.
- The preview without a login shows the same thing with sample data.

## Out of scope

- Checking that the prize was actually given or the task was done.
- Removing or editing a suggestion.
- Paying for a prize from the fund.
- Reminders or notifications.

## Done when

- The rules are pure functions in `logic.py`, and all saving is in `db.py`.
- The owner of the tables in `db.py` has agreed to the two new tables before
  this is merged.
- Tests cover suggesting (tidied, empty, too long, duplicate, too many, after
  Wednesday), voting (accepted, twice, after Wednesday, last week's option, one
  vote in each of the two votes), the database refusing a second vote, the
  chosen option (most votes, ties, no votes), last week's winners and losers
  (ties, everyone equal), and another flat not seeing or voting on the prizes.
- `uv run pytest` passes.
