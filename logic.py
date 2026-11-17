"""The rules of the app. Pure functions only: no Streamlit and no database here."""

import ipaddress
import secrets
from datetime import date, timedelta

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
