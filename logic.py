"""The rules of the app. Pure functions only: no Streamlit and no database here."""

import csv
import io
import ipaddress
import secrets
from datetime import date, datetime, timedelta
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


# --- Avatars (specs/design.md) -------------------------------------------------

AVATAR_EMOJIS = ("🦊", "🐻", "🐼", "🐨", "🐸", "🐙", "🦄", "🐱", "🐶", "🐧", "🦉", "🐢", "🌻", "🌵", "🍕", "🎸")
# Streamlit's own background colours, used as ":orange-background[🦊]" in markdown (no HTML needed).
AVATAR_COLORS = ("red", "orange", "yellow", "green", "blue", "violet", "gray")
DEFAULT_AVATAR = ("🙂", "gray")


def check_avatar(emoji: str, color: str) -> tuple[str, str]:
    """Return the avatar, or raise ValueError unless both the emoji and the colour are from the lists."""
    if emoji not in AVATAR_EMOJIS:
        raise ValueError("Pick one of the emojis in the list.")
    if color not in AVATAR_COLORS:
        raise ValueError("Pick one of the colours in the list.")
    return emoji, color


def avatar_label(emoji: str | None, color: str | None) -> str:
    """The avatar as Streamlit markdown: the emoji on its colour, or the default if none is picked."""
    if emoji is None or color is None:
        emoji, color = DEFAULT_AVATAR
    return f":{color}-background[{emoji}]"


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


def check_deadline(due_on: date | None, today: date) -> date | None:
    """Return the deadline, or raise ValueError if it is in the past. No deadline (None) is fine."""
    if due_on is not None and due_on < today:
        raise ValueError("The deadline cannot be in the past.")
    return due_on


def deadline_status(due_on: date | None, today: date) -> str | None:
    """Return 'overdue' if the deadline has passed, 'today' if it is today, else None."""
    if due_on is None or due_on > today:
        return None
    return "today" if due_on == today else "overdue"


def done_before_this_week(done_at: datetime, today: date) -> bool:
    """True if a chore was done before Monday of this week, so it belongs in the history."""
    return done_at.date() < week_start(today)


def my_chores_summary(chores: list[dict], user_id: int, today: date, next_count: int = 3) -> dict:
    """Numbers for the Flat tab overview: one member's open and overdue chores, points this week,
    and their next chores (soonest deadline first, chores without a deadline last).

    chores are dicts with 'assigned_to', 'points', 'done', 'done_at' and 'due_on', as from db.list_chores.
    """
    mine = [chore for chore in chores if chore["assigned_to"] == user_id]
    open_chores = [chore for chore in mine if not chore["done"]]
    points = sum(
        chore["points"] for chore in mine if chore["done"] and not done_before_this_week(chore["done_at"], today)
    )
    soonest_first = sorted(open_chores, key=lambda chore: (chore["due_on"] is None, chore["due_on"] or today))
    return {
        "open": len(open_chores),
        "overdue": sum(deadline_status(chore["due_on"], today) == "overdue" for chore in open_chores),
        "points": points,
        "next": soonest_first[:next_count],
    }


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


# --- Activity ideas from the weather (specs/activity-suggestions.md) ----------

MAX_ACTIVITY_LENGTH = 40
MAX_ACTIVITY_COST = 1000.0
MAX_SUGGESTIONS = 3
BEACH_TEMPERATURE = 22  # highest temperature today, in °C
OUTSIDE_TEMPERATURE = 15
WET_RAIN_CHANCE = 70  # percent

# WMO weather codes, as used by Open-Meteo: https://open-meteo.com/en/docs
WEATHER_KINDS = {
    "sunny": {0, 1},
    "cloudy": {2, 3},
    "foggy": {45, 48},
    "rainy": {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82},
    "snowy": {71, 73, 75, 77, 85, 86},
    "stormy": {95, 96, 99},
}

BEACH_IDEAS = [
    {"activity": "Beach day", "cost": 10.0, "why": "Warm and dry: pack a towel and some snacks."},
]
OUTSIDE_IDEAS = [
    {"activity": "Picnic in the park", "cost": 15.0, "why": "Dry and mild, good for eating outside."},
    {"activity": "Sunset at a viewpoint", "cost": 12.0, "why": "A clear evening to watch the sun go down."},
    {"activity": "Walk and coffee in town", "cost": 10.0, "why": "Nice weather for a walk together."},
]
INSIDE_IDEAS = [
    {"activity": "Board game evening", "cost": 0.0, "why": "Stay in and keep dry."},
    {"activity": "Cook a big dinner together", "cost": 30.0, "why": "A cosy evening in the kitchen."},
    {"activity": "Movie night", "cost": 10.0, "why": "Popcorn on the sofa while it is grey outside."},
]


def weather_kind(code: int) -> str:
    """Turn a WMO weather code into a simple kind of weather, or raise ValueError if it is unknown."""
    for kind, codes in WEATHER_KINDS.items():
        if code in codes:
            return kind
    raise ValueError(f"Unknown weather code {code}.")


def parse_weather(data: dict) -> dict:
    """Read today's weather from an Open-Meteo forecast, or raise ValueError if it is missing."""
    try:
        current = data["current"]
        temperature = float(current["temperature_2m"])
        kind = weather_kind(int(current["weather_code"]))
        wind = float(current.get("wind_speed_10m", 0))
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("The weather could not be read.") from error
    daily = data.get("daily") or {}
    highs = daily.get("temperature_2m_max") or [temperature]
    rain = daily.get("precipitation_probability_max") or [0]
    return {
        "kind": kind,
        "temperature": temperature,
        "max_temperature": float(highs[0] if highs[0] is not None else temperature),
        "rain_chance": int(rain[0] or 0),
        "wind": wind,
    }


def parse_location(data: dict) -> dict:
    """Read the city and coordinates from an ipinfo.io answer, or raise ValueError if there are none."""
    if data.get("bogon"):
        raise ValueError("A local or private address has no location.")
    try:
        lat, lon = (float(part) for part in data["loc"].split(","))
    except (KeyError, AttributeError, ValueError) as error:
        raise ValueError("The location could not be read.") from error
    return {"city": data.get("city") or "your area", "country": data.get("country") or "", "lat": lat, "lon": lon}


def pick_client_ip(forwarded_for: str | None, remote_ip: str | None) -> str | None:
    """Return the visitor's first public IP address, or None if only local or private ones are known."""
    candidates = [part.strip() for part in (forwarded_for or "").split(",")] + [remote_ip or ""]
    for candidate in candidates:
        try:
            if ipaddress.ip_address(candidate).is_global:
                return candidate
        except ValueError:
            continue
    return None


def _is_new(name: str, taken: set[str]) -> bool:
    return name.lower() not in taken


def rule_suggestions(weather: dict, existing: list[str]) -> list[dict]:
    """Ideas for today from the weather. Skips ideas already on the list."""
    wet = weather["kind"] in ("rainy", "snowy", "stormy", "foggy") or weather["rain_chance"] >= WET_RAIN_CHANCE
    if not wet and weather["max_temperature"] >= BEACH_TEMPERATURE:
        pool = BEACH_IDEAS + OUTSIDE_IDEAS
    elif not wet and weather["max_temperature"] >= OUTSIDE_TEMPERATURE:
        pool = OUTSIDE_IDEAS
    else:
        pool = INSIDE_IDEAS
    taken = {name.lower() for name in existing}
    ideas = [dict(idea) for idea in pool + INSIDE_IDEAS if _is_new(idea["activity"], taken)]
    unique = list({idea["activity"]: idea for idea in ideas}.values())
    return unique[:MAX_SUGGESTIONS]


# --- Voting on activities (specs/activity-voting.md) ---------------------------
# A vote is {"activity": name, "who": member name, "day": date}.


def check_can_vote(activities: list[str], votes: list[dict], activity: str, who: str, today: date) -> None:
    """Raise ValueError if this member may not vote for this activity today: once per activity, once per day."""
    if activity not in activities:
        raise ValueError(f"{activity} is not on the list.")
    mine = [vote for vote in votes if vote["who"] == who]
    if any(vote["activity"] == activity for vote in mine):
        raise ValueError(f"You already voted for {activity}.")
    for vote in mine:
        if vote["day"] == today:
            raise ValueError(f"You already voted today, for {vote['activity']}. You can vote again tomorrow.")


def voters(votes: list[dict], activity: str) -> list[str]:
    """Names of the members who voted for an activity, in the order they voted."""
    return [vote["who"] for vote in votes if vote["activity"] == activity]


def rank_activities(activities: list[dict], votes: list[dict]) -> list[tuple[dict, list[str]]]:
    """Each activity with its voters, most votes first; ties sorted by name."""
    ranked = [(activity, voters(votes, activity["activity"])) for activity in activities]
    return sorted(ranked, key=lambda pair: (-len(pair[1]), pair[0]["activity"].lower()))


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


# --- House rules (specs/house-rules.md) ----------------------------------------

MAX_RULE_LENGTH = 120


def rule_key(text: str) -> str:
    """The form used to compare rules: spaces tidied and capital letters ignored."""
    return " ".join(text.split()).casefold()


def clean_rule(raw: str, existing: list[str] = ()) -> str:
    """Return a tidy house rule, or raise ValueError if it is empty, too long or already on the list."""
    rule = _tidy_text(raw, "Rule", MAX_RULE_LENGTH)
    if rule_key(rule) in {rule_key(other) for other in existing}:
        raise ValueError("That rule is already on the list.")
    return rule


def votes_needed(members: int) -> int:
    """How many votes are a majority: more than half of the members."""
    if members < 1:
        raise ValueError("A flat needs at least one member to vote.")
    return members // 2 + 1


def has_majority(votes: int, members: int) -> bool:
    """True if this many votes are more than half of the members."""
    return votes >= votes_needed(members)


def check_can_vote_to_remove(voters: list, who) -> None:
    """Raise ValueError if this member already voted to remove this rule: everyone votes once."""
    if who in voters:
        raise ValueError("You already voted to remove this rule.")
