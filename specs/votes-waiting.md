# Votes waiting for you

## Why

The flat votes on prizes, activities and house rules, but those votes live on
different tabs, so people miss them. When a member opens the app, the first
thing they should see is what is waiting for their vote, and they should be
able to vote right there.

## What

- At the top of the Today tab, a **Needs your vote** tile lists what is waiting
  for this member, most urgent first:
  1. **Weekly prize:** what the winner gets and what the loser has to do, while
     voting is open (Monday to Wednesday), if the vote has options and the
     member has not voted in it. It says when voting closes.
  2. **House rules:** a rule that at least one flatmate has voted to remove,
     if this member has not voted on it. It shows the votes so far and how
     many are needed.
  3. **Activities:** if the member has not used today's vote and there is an
     activity they can still vote for. Activities whose date has passed are
     not offered. The 3 with the most votes are shown, and a button opens the
     Activities tab when there are more.
- A member can vote with one tap in the tile. The same rules apply as on the
  other tabs, and a vote cannot be taken back.
- **Not now** hides an item until the member's next visit. It does not count
  as a vote. A hidden prize or activity vote comes back the next time they
  open the app, and nobody else can see that it was hidden.
- When nothing is waiting, a short line says so.
- The tile refreshes itself with the rest of Today
  (`specs/live-updates.md`), so a flatmate's new suggestion shows up.
- Today still loads in one database visit (`specs/speed.md`).
- The preview without a login shows the same tile with sample data.

## Out of scope

- A way to vote to keep a rule.
- Remembering **Not now** between visits.
- Notifications, emails or badges outside the app.

## Done when

- What is waiting is decided by a pure function in `logic.py`.
- Tests cover each kind of vote being shown and not shown: voted already,
  voting closed, no options, no votes on a rule, past activities, hidden with
  Not now, the order, and another flat's votes never showing up.
- The Today speed tests still pass unchanged.
- `uv run pytest` passes.
