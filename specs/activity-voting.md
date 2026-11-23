# Voting on activities

## Why

The flat votes on what to do together. Votes only mean something if they are
fair: everyone can see who voted for what, nobody can vote for the same thing
twice, and nobody can flood the list by voting for everything at once.

## What

- Every activity on the flat's list shows how many votes it has and the names
  of the members who voted for it, in the order they voted.
- The list is sorted by number of votes, highest first. Activities with the
  same number of votes are sorted by name.
- A member can vote for an activity only once.
- A member can vote at most once per day, for one activity. The next day they
  can vote again, for another activity.
- When a member cannot vote, the vote button is turned off and says why:
  they already voted for this activity, or they already voted today (and for
  which activity).
- Voting for an activity that is not on the list is rejected.

## Out of scope

- Taking back or changing a vote.
- Votes that expire, or starting a new round of voting.

## Done when

- The rules are pure functions in `logic.py`.
- Tests cover an accepted vote, voting twice for the same activity, a second
  vote on the same day, voting again the next day, a vote for an activity
  that is not on the list, the list of voters, and the sorting.
- `uv run pytest` passes.
