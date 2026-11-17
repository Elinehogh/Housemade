# Shopping

## Why

Someone always runs out of toilet paper, and nobody remembers who paid for
the last dish soap. Housemade keeps one shared shopping list for the flat,
splits shared costs equally, and shows who owes whom until it is paid back.

## What

Shopping list:

- Any member can add items to their own flat's list. They can pick common
  flat items from a list (toilet paper, kitchen roll, dish soap, laundry
  detergent and more) or type their own.
- An item name is 1 to 40 characters. Extra spaces are removed.
- The same item cannot be on the open list twice (upper and lower case count
  as the same).
- Ticking an item off saves who bought it and when.
- Any member can remove an item, and clear all bought items at once.

Shared costs:

- A member registers what they paid for the flat: an amount and what it was
  for (1 to 40 characters). You can only register costs you paid yourself.
- An amount is more than €0 and at most €10,000, with at most 2 decimals.
  Money is stored in whole cents, so no cents are lost to rounding.
- Every cost is split equally between all members of the flat. When it does
  not split evenly, the leftover cents go to members one by one, so the
  balances always add up to exactly zero.
- Balances show how much each member should get back or owes, and a short
  list of payments that settles everything ("Tom pays Ana €5.00").

Paying back:

- The person who receives money confirms it: "Tom paid me €5.00". Only the
  receiver can confirm, so nobody can mark their own debt as paid.
- You cannot confirm a payment from yourself, or from someone outside your
  flat.
- A confirmed payment changes the balances right away.

Everything is saved in the database. Members only see and change the list,
costs and payments of their own flat.

## Out of scope

- Splitting a cost between only some members, or unequally.
- Editing or deleting a cost or a payment.
- Prices or shops for items on the list.
- Members who join later share the costs from before they joined.
- Paying through the app (it only records payments made elsewhere).

## Done when

- The shopping list, costs and payments are saved in the database, not in the
  sample data.
- Tests cover accepted and rejected actions: an empty or too long item, a
  duplicate item, buying an item twice or from another flat, an amount of 0,
  below 0, over the limit or with 3 decimals, uneven splits, confirming a
  payment from yourself or from another flat, and another flat's data.
- `uv run pytest` passes.
- It works on https://housemade.streamlit.app/, not only locally.
