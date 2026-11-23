# House rules

## Why

Most arguments in a shared flat come from expectations nobody said out loud.
A shared list of house rules makes them clear. Everyone can add a rule, and no
single person can remove one: the flat decides together.

## What

- A House rules tab lists the rules of the member's own flat, oldest first,
  with who added each rule and when.
- Any member can add a rule. A rule is 1 to 120 characters. Extra spaces are
  removed.
- A flat cannot have the same rule twice (capital letters do not matter).
  Two different flats can have the same rule.
- Any member can vote to remove a rule, including the person who added it.
- Each member can vote once per rule. A vote cannot be taken back.
- A rule is removed as soon as a majority of the flat has voted for it, which
  means more than half of the members: 1 of 1, 2 of 2, 2 of 3, 3 of 4, 3 of 5.
- Each rule shows how many votes it has, how many it needs, and who voted.
- A removed rule can be added again later, and starts with no votes.
- The list refreshes itself like the other shared lists
  (`specs/live-updates.md`). The add form stays outside the refreshing part.
- The preview shows sample rules. Nothing is saved there.

## Out of scope

- Editing a rule.
- Voting before a new rule is accepted.
- Penalties or reminders when a rule is broken.

## Done when

- The rules are pure functions in `logic.py`, and rules and votes are saved
  through `db.py`.
- The owner of the tables in `db.py` has agreed to the two new tables before
  this is merged.
- Tests cover adding a rule (tidied, empty, too long, duplicate, same rule in
  another flat), voting (first vote, voting twice, a rule from another flat, a
  rule that does not exist), the majority for different flat sizes, removal
  at exactly the majority, and adding a removed rule again.
- `uv run pytest` passes.
