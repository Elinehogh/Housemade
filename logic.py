"""The rules of the app. Pure functions only: no Streamlit and no database here."""

import secrets

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
