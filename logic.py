"""The rules of the app. Pure functions only: no Streamlit and no database here."""

import csv
import io
import secrets
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

MAX_NAME_LENGTH = 30
MAX_FLAT_NAME_LENGTH = 40

# No 0/O or 1/I/L, so codes are easy to read out loud and type.
INVITE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
INVITE_CODE_LENGTH = 6

ROLES = ("admin", "member")


def clean_member_name(raw: str) -> str:
    """Return a tidy member name, or raise ValueError if it is not allowed."""
    name = " ".join(raw.split())
    if not name:
        raise ValueError("Name cannot be empty.")
    if len(name) > MAX_NAME_LENGTH:
        raise ValueError(f"Name can be at most {MAX_NAME_LENGTH} characters.")
    return name


def display_name(google_name: str | None, email: str) -> str:
    """Pick a member name from the Google account: its name, shortened if needed, or the start of the email."""
    name = " ".join((google_name or "").split())[:MAX_NAME_LENGTH].strip()
    return name or email.split("@")[0][:MAX_NAME_LENGTH]


def clean_amount(raw: float) -> float:
    """Return a money amount rounded to cents, or raise ValueError if it is not positive."""
    amount = round(float(raw), 2)
    if amount <= 0:
        raise ValueError("Amount must be more than €0.")
    return amount


def balances(members: list[str], payments: list[tuple[str, float]]) -> dict[str, float]:
    """Split shared costs equally. Positive: the flat owes this member. Negative: they owe the flat.

    The balances always add up to zero (up to rounding by a few cents).
    """
    if not members:
        return {}
    total = sum(amount for _, amount in payments)
    share = total / len(members)
    paid = {name: 0.0 for name in members}
    for name, amount in payments:
        if name not in paid:
            raise ValueError(f"{name} is not a member of the flat.")
        paid[name] += amount
    return {name: round(paid[name] - share, 2) for name in members}


def clean_flat_name(raw: str) -> str:
    """Return a tidy flat name, or raise ValueError if it is not allowed."""
    name = " ".join(raw.split())
    if not name:
        raise ValueError("Flat name cannot be empty.")
    if len(name) > MAX_FLAT_NAME_LENGTH:
        raise ValueError(f"Flat name can be at most {MAX_FLAT_NAME_LENGTH} characters.")
    return name


def new_invite_code() -> str:
    """Return a random invite code, for example 'K7QX2M'."""
    return "".join(secrets.choice(INVITE_ALPHABET) for _ in range(INVITE_CODE_LENGTH))


def clean_invite_code(raw: str) -> str:
    """Return the code as stored (upper case, no spaces), or raise ValueError."""
    code = "".join(raw.split()).upper()
    if len(code) != INVITE_CODE_LENGTH or any(c not in INVITE_ALPHABET for c in code):
        raise ValueError(f"An invite code has {INVITE_CODE_LENGTH} letters and digits.")
    return code


# --- Chores ------------------------------------------------------------------

MAX_CHORE_LENGTH = 40
MIN_POINTS = 1
MAX_POINTS = 10
DEFAULT_POINTS = 2

# Chores most flats have, with suggested points: bigger jobs give more points.
COMMON_CHORES = {
    "Clean the bathroom": 5,
    "Clean the kitchen": 4,
    "Vacuum": 3,
    "Mop the floors": 3,
    "Do the dishes": 2,
    "Take out the trash": 1,
    "Take out the recycling": 1,
    "Return bottles and cans": 2,
    "Wipe the kitchen counters": 1,
    "Clean the fridge": 3,
    "Clean the oven": 5,
    "Dust the shelves": 2,
    "Clean the windows": 4,
    "Change the towels": 1,
    "Water the plants": 1,
}


def clean_chore_name(raw: str) -> str:
    """Return a tidy chore name, or raise ValueError if it is not allowed."""
    name = " ".join(raw.split())
    if not name:
        raise ValueError("Chore cannot be empty.")
    if len(name) > MAX_CHORE_LENGTH:
        raise ValueError(f"Chore can be at most {MAX_CHORE_LENGTH} characters.")
    return name


def clean_points(raw: float) -> int:
    """Return the points as a whole number, or raise ValueError if they are not allowed."""
    if raw != int(raw):
        raise ValueError("Points must be a whole number.")
    points = int(raw)
    if not MIN_POINTS <= points <= MAX_POINTS:
        raise ValueError(f"Points must be from {MIN_POINTS} to {MAX_POINTS}.")
    return points


def suggested_points(name: str | None) -> int:
    """Return the suggested points for a chore: from COMMON_CHORES if it is one, else DEFAULT_POINTS."""
    wanted = " ".join((name or "").split()).lower()
    for chore, points in COMMON_CHORES.items():
        if chore.lower() == wanted:
            return points
    return DEFAULT_POINTS


def check_can_tick_off(assigned_to: int, is_done: bool, user_id: int) -> None:
    """Raise ValueError unless this user may tick off this chore now."""
    if assigned_to != user_id:
        raise ValueError("Only the person the chore is given to can tick it off.")
    if is_done:
        raise ValueError("This chore is already done.")


def week_start(day: date) -> date:
    """Return the Monday of the week that this day is in."""
    return day - timedelta(days=day.weekday())


def leaderboard(members: dict[int, str], done: list[tuple[int, int]]) -> list[tuple[str, int]]:
    """Rank members by points: highest first, then by name. Members without points get 0.

    members maps user id to name. done is a list of (user id, points) for finished chores.
    """
    points = {user_id: 0 for user_id in members}
    for user_id, chore_points in done:
        if user_id not in points:
            raise ValueError("Only members of the flat can get points.")
        points[user_id] += chore_points
    ranking = [(members[user_id], total) for user_id, total in points.items()]
    return sorted(ranking, key=lambda item: (-item[1], item[0]))


# --- Fund --------------------------------------------------------------------

MAX_FUND_AMOUNT = 1000  # euros per entry
MAX_DESCRIPTION_LENGTH = 40


def to_cents(raw: float) -> int:
    """Return a fund amount as whole cents, or raise ValueError if it is not allowed."""
    amount = clean_amount(raw)
    if amount > MAX_FUND_AMOUNT:
        raise ValueError(f"Amount can be at most €{MAX_FUND_AMOUNT}.")
    return round(amount * 100)


def format_euros(cents: int) -> str:
    """Show cents as euros, for example 640 -> '€6.40' and -2400 -> '-€24.00'."""
    sign = "-" if cents < 0 else ""
    return f"{sign}€{abs(cents) // 100}.{abs(cents) % 100:02d}"


def clean_description(raw: str) -> str:
    """Return a tidy description of a fund entry, or raise ValueError if it is not allowed."""
    text = " ".join(raw.split())
    if not text:
        raise ValueError("Description cannot be empty.")
    if len(text) > MAX_DESCRIPTION_LENGTH:
        raise ValueError(f"Description can be at most {MAX_DESCRIPTION_LENGTH} characters.")
    return text


def check_can_take_out(balance_cents: int, amount_cents: int) -> None:
    """Raise ValueError if taking this amount out would make the fund go below zero."""
    if amount_cents > balance_cents:
        raise ValueError(f"The fund only has {format_euros(balance_cents)}. It cannot go below zero.")


def goal_progress(balance_cents: int, goal_cents: int) -> float:
    """Return how far the fund has come towards the goal, from 0.0 to 1.0."""
    if goal_cents <= 0:
        return 0.0
    return min(max(balance_cents / goal_cents, 0.0), 1.0)


def fund_csv(entries: list[dict]) -> str:
    """Return the fund history as CSV text. Each entry has 'date', 'what', 'who' and 'cents'."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["date", "what", "who", "amount_eur"])
    for entry in entries:
        euros = format_euros(entry["cents"]).replace("€", "")
        writer.writerow([entry["date"].isoformat(), entry["what"], entry["who"], euros])
    return out.getvalue()


# --- Shopping ----------------------------------------------------------------

MAX_ITEM_LENGTH = 40
MAX_AMOUNT_CENTS = 1_000_000  # €10,000

# Things a flat often runs out of, offered in a list so nobody has to type them.
COMMON_ITEMS = (
    "Toilet paper",
    "Kitchen roll",
    "Dish soap",
    "Dishwasher tablets",
    "Laundry detergent",
    "Hand soap",
    "Bin bags",
    "Sponges",
    "Cleaning spray",
    "Toilet cleaner",
    "Aluminium foil",
    "Cling film",
    "Coffee",
    "Salt",
    "Cooking oil",
)


def _tidy_text(raw: str, what: str, max_length: int) -> str:
    text = " ".join(raw.split())
    if not text:
        raise ValueError(f"{what} cannot be empty.")
    if len(text) > max_length:
        raise ValueError(f"{what} can be at most {max_length} characters.")
    return text


def clean_item_name(raw: str) -> str:
    """Return a tidy shopping item, or raise ValueError if it is not allowed."""
    return _tidy_text(raw, "Item", MAX_ITEM_LENGTH)


def cost_to_cents(raw) -> int:
    """Turn an amount in euros (for example 18.4 or "12.50") into whole cents, or raise ValueError.

    Allowed: more than €0, at most €10,000, and at most 2 decimals.
    """
    try:
        # str() first, so 18.4 becomes exactly 18.4 and not 18.399999...
        amount = Decimal(str(raw))
    except InvalidOperation:
        raise ValueError("Amount must be a number.") from None
    if not amount.is_finite():
        raise ValueError("Amount must be a number.")
    cents = amount * 100
    if cents != cents.to_integral_value():
        raise ValueError("Amount can have at most 2 decimals.")
    cents = int(cents)
    if cents <= 0:
        raise ValueError("Amount must be more than €0.")
    if cents > MAX_AMOUNT_CENTS:
        raise ValueError(f"Amount can be at most {format_euros(MAX_AMOUNT_CENTS)}.")
    return cents


def split_cents(total: int, people: int) -> list[int]:
    """Split cents as equally as possible. Leftover cents go to the first people, so nothing is lost."""
    if people <= 0:
        raise ValueError("A cost must be split between at least one person.")
    share, leftover = divmod(total, people)
    return [share + 1 if i < leftover else share for i in range(people)]


def shopping_balances(
    members: list[int], expenses: list[tuple[int, int]], payments: list[tuple[int, int, int]]
) -> dict[int, int]:
    """Return each member's balance in cents. Positive: they should get money back. Negative: they owe.

    members: user ids. expenses: (who paid, cents), split equally between all members.
    payments: (payer, receiver, cents) for money paid back. The balances always add up to exactly 0.
    """
    order = sorted(members)
    balance = {user_id: 0 for user_id in order}

    def check_member(user_id):
        if user_id not in balance:
            raise ValueError("Only members of the flat can share costs.")

    for payer, cents in expenses:
        check_member(payer)
        balance[payer] += cents
        for user_id, share in zip(order, split_cents(cents, len(order))):
            balance[user_id] -= share
    for payer, receiver, cents in payments:
        check_member(payer)
        check_member(receiver)
        balance[payer] += cents
        balance[receiver] -= cents
    return balance


def settle_up(balances: dict[int, int]) -> list[tuple[int, int, int]]:
    """Return a short list of (payer, receiver, cents) that makes every balance 0.

    The biggest debts are paid to the biggest creditors first.
    """
    biggest_first = sorted(balances.items(), key=lambda item: (-abs(item[1]), item[0]))
    owes = [[user_id, -cents] for user_id, cents in biggest_first if cents < 0]
    gets = [[user_id, cents] for user_id, cents in biggest_first if cents > 0]
    transfers = []
    for debtor in owes:
        for creditor in gets:
            cents = min(debtor[1], creditor[1])
            if cents > 0:
                transfers.append((debtor[0], creditor[0], cents))
                debtor[1] -= cents
                creditor[1] -= cents
    return transfers


def check_payment(payer: int, receiver: int, confirmed_by: int, members: list[int]) -> None:
    """Raise ValueError unless this payment may be confirmed.

    Only the person who received the money can confirm it, so nobody can mark their own debt as paid.
    """
    if payer not in members or receiver not in members:
        raise ValueError("Payments can only be between members of your flat.")
    if payer == receiver:
        raise ValueError("You cannot pay yourself.")
    if confirmed_by != receiver:
        raise ValueError("Only the person who got the money can confirm a payment.")
