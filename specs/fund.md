# Fund

## Why

A flat often has bottles and cans that give deposit money (pant), and small
shared costs like a pizza night. Housemade collects that money in a shared
fund, so the flat can save up for something to do together. The fund ties
chores and pant to the activities.

## What

- Any member can add pant money to their own flat's fund. It is saved with
  their name and the date.
- The admin can take money out of the fund for a shared cost, with a short
  description of what it was for.
- The fund can never go below zero: taking out more than is in the fund is
  rejected.
- An amount is more than €0 and at most €1000, rounded to cents. Money is
  stored as whole cents, so sums are always exact.
- A description is 1 to 40 characters. Extra spaces are removed.
- The admin can set one savings goal for the flat (a name and an amount). The
  screen shows how far the fund has come towards it.
- Everyone in the flat sees the balance and the full history, newest first,
  and can download the history as a CSV file.
- The balance always equals the sum of the history.
- Each member only sees and changes the fund of their own flat.

## Out of scope

- Editing or deleting an entry. A mistake is fixed with a new entry.
- Linking the fund to the activities tab (the "can we afford it" filter is
  part of the activities feature).
- Real payments, bank accounts or MB Way.

## Done when

- Fund entries and the goal are saved in the database, not in the sample data.
- Tests cover accepted and rejected actions: 0, negative and too large
  amounts, an empty or too long description, a member trying to take money
  out, taking out more than the balance, and another flat's fund.
- A test checks that the balance equals the sum of the history and of the CSV.
- `uv run pytest` passes.
- It works on https://housemade.streamlit.app/, not only locally.
