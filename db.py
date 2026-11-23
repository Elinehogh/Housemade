"""Storage. Every read and write of saved data goes through this file.

The deployed app uses a hosted Postgres database (Supabase). Tests and local
runs without a secret use SQLite. Both are reached through SQLAlchemy, so the
functions below work the same on either.

Access control: functions that read or change a flat's data take the user's
id, not a flat id, and look up the user's own flat. A user can never reach
another flat's data by passing a different id.
"""

from datetime import date, datetime, time, timedelta

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    create_engine,
    delete,
    event,
    func,
    insert,
    inspect,
    literal_column,
    null,
    select,
    text,
    union_all,
    update,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from logic import (
    INVITE_CODE_LENGTH,
    MAX_ACTIVITY_COST,
    MAX_ACTIVITY_LENGTH,
    MAX_AMOUNT_CENTS,
    MAX_CHORE_LENGTH,
    MAX_DESCRIPTION_LENGTH,
    MAX_FLAT_NAME_LENGTH,
    MAX_ITEM_LENGTH,
    MAX_NAME_LENGTH,
    MAX_POINTS,
    MAX_PRIZE_LENGTH,
    MAX_RULE_LENGTH,
    MIN_POINTS,
    PRIZE_KINDS,
    ROLES,
    activity_cost_cents,
    activity_key,
    check_activity_date,
    check_can_remove_activity,
    check_can_suggest_prize,
    check_can_take_out,
    check_can_tick_off,
    check_can_vote,
    check_can_vote_prize,
    check_can_vote_to_remove,
    check_deadline,
    check_payment,
    chosen_prize,
    clean_activity_name,
    clean_chore_name,
    clean_description,
    clean_flat_name,
    clean_invite_code,
    clean_item_name,
    clean_member_name,
    check_avatar,
    clean_points,
    clean_prize,
    clean_rule,
    cost_to_cents,
    has_majority,
    leaderboard,
    new_invite_code,
    prize_key,
    rank_activities,
    rule_key,
    settle_up,
    shopping_balances,
    to_cents,
    votes_needed,
    voting_is_open,
    week_result,
    week_start,
)

CONNECT_TIMEOUT_SECONDS = 5  # give up quickly if the database cannot be reached (specs/reliability.md)

metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("email", String(254), nullable=False, unique=True),
    Column("name", String(MAX_NAME_LENGTH), nullable=False),
    # Empty until the user picks an avatar (logic.AVATAR_EMOJIS and logic.AVATAR_COLORS).
    Column("avatar_emoji", String(8), nullable=True),
    Column("avatar_color", String(10), nullable=True),
)

flats = Table(
    "flats",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(MAX_FLAT_NAME_LENGTH), nullable=False),
    Column("invite_code", String(INVITE_CODE_LENGTH), nullable=False, unique=True),
)

# A user belongs to at most one flat (unique user_id).
memberships = Table(
    "memberships",
    metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("flat_id", ForeignKey("flats.id"), nullable=False),
    Column("role", String(10), nullable=False),
    CheckConstraint(f"role IN {ROLES}", name="valid_role"),
)

# A chore belongs to one flat and is given to one member. done_at is empty until it is ticked off.
# New columns must be nullable, so _add_missing_columns() can add them to an existing database.
chores = Table(
    "chores",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("flat_id", ForeignKey("flats.id"), nullable=False),
    Column("name", String(MAX_CHORE_LENGTH), nullable=False),
    Column("points", Integer, nullable=False),
    Column("assigned_to", ForeignKey("users.id"), nullable=False),
    Column("done_at", DateTime, nullable=True),
    Column("due_on", Date, nullable=True),  # The deadline. Empty: no deadline.
    CheckConstraint(f"points BETWEEN {MIN_POINTS} AND {MAX_POINTS}", name="valid_points"),
)

# Shopping list. bought_by and bought_at are empty until someone buys the item.
shopping_items = Table(
    "shopping_items",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("flat_id", ForeignKey("flats.id"), nullable=False),
    Column("name", String(MAX_ITEM_LENGTH), nullable=False),
    Column("added_by", ForeignKey("users.id"), nullable=False),
    Column("bought_by", ForeignKey("users.id"), nullable=True),
    Column("bought_at", DateTime, nullable=True),
)

# A shared cost, paid by one member and split equally between the flat. Money is in whole cents.
expenses = Table(
    "expenses",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("flat_id", ForeignKey("flats.id"), nullable=False),
    Column("paid_by", ForeignKey("users.id"), nullable=False),
    Column("amount_cents", Integer, nullable=False),
    Column("description", String(MAX_DESCRIPTION_LENGTH), nullable=False),
    Column("created_at", DateTime, nullable=False),
    CheckConstraint(f"amount_cents BETWEEN 1 AND {MAX_AMOUNT_CENTS}", name="valid_expense"),
)

# Money paid back from one member to another, confirmed by the one who received it.
payments = Table(
    "payments",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("flat_id", ForeignKey("flats.id"), nullable=False),
    Column("from_user", ForeignKey("users.id"), nullable=False),
    Column("to_user", ForeignKey("users.id"), nullable=False),
    Column("amount_cents", Integer, nullable=False),
    Column("created_at", DateTime, nullable=False),
    CheckConstraint(f"amount_cents BETWEEN 1 AND {MAX_AMOUNT_CENTS}", name="valid_payment"),
    CheckConstraint("from_user <> to_user", name="not_to_yourself"),
)

# Money in (pant, positive cents) and out (shared costs, negative cents) of a flat's fund.
# Whole cents, so sums are exact. The balance is the sum of all entries.
fund_entries = Table(
    "fund_entries",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("flat_id", ForeignKey("flats.id"), nullable=False),
    Column("user_id", ForeignKey("users.id"), nullable=False),
    Column("what", String(MAX_DESCRIPTION_LENGTH), nullable=False),
    Column("cents", Integer, nullable=False),
    Column("created_at", DateTime, nullable=False),
    CheckConstraint("cents <> 0", name="nonzero_cents"),
)

# At most one savings goal per flat.
fund_goals = Table(
    "fund_goals",
    metadata,
    Column("flat_id", ForeignKey("flats.id"), primary_key=True),
    Column("name", String(MAX_DESCRIPTION_LENGTH), nullable=False),
    Column("cents", Integer, nullable=False),
    CheckConstraint("cents > 0", name="positive_goal"),
)

# Things a flat can do together. name_key is the name without capitals, so a flat cannot have the same
# activity twice. It is longer than the name because ignoring capitals can make a few letters longer.
activities = Table(
    "activities",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("flat_id", ForeignKey("flats.id"), nullable=False),
    Column("name", String(MAX_ACTIVITY_LENGTH), nullable=False),
    Column("name_key", String(MAX_ACTIVITY_LENGTH * 3), nullable=False),
    Column("cost_cents", Integer, nullable=False),
    Column("planned_on", Date, nullable=False),
    Column("added_by", ForeignKey("users.id"), nullable=False),
    Column("created_at", DateTime, nullable=False),
    UniqueConstraint("flat_id", "name_key", name="one_activity_per_flat"),
    CheckConstraint(f"cost_cents BETWEEN 0 AND {int(MAX_ACTIVITY_COST * 100)}", name="valid_activity_cost"),
)

# Votes on activities. The primary key allows one vote per member per activity,
# and the unique constraint one vote per member per day. A user belongs to one flat.
activity_votes = Table(
    "activity_votes",
    metadata,
    Column("activity_id", ForeignKey("activities.id"), primary_key=True),
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("voted_on", Date, nullable=False),
    UniqueConstraint("user_id", "voted_on", name="one_vote_per_day"),
)

# What the winner of a week gets and what the loser has to do: the options the flat suggests.
# name_key is the name without capitals, so the same option cannot be suggested twice in one vote.
weekly_prizes = Table(
    "weekly_prizes",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("flat_id", ForeignKey("flats.id"), nullable=False),
    Column("week_start", Date, nullable=False),  # the Monday of the week
    Column("kind", String(10), nullable=False),
    Column("name", String(MAX_PRIZE_LENGTH), nullable=False),
    Column("name_key", String(MAX_PRIZE_LENGTH * 3), nullable=False),
    Column("added_by", ForeignKey("users.id"), nullable=False),
    Column("created_at", DateTime, nullable=False),
    UniqueConstraint("flat_id", "week_start", "kind", "name_key", name="one_prize_option_per_vote"),
    CheckConstraint(f"kind IN {PRIZE_KINDS}", name="valid_prize_kind"),
)

# The primary key allows each member one vote per week in each of the two votes.
# A user belongs to one flat, so this holds per flat too.
weekly_prize_votes = Table(
    "weekly_prize_votes",
    metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("week_start", Date, primary_key=True),
    Column("kind", String(10), primary_key=True),
    Column("prize_id", ForeignKey("weekly_prizes.id"), nullable=False),
    CheckConstraint(f"kind IN {PRIZE_KINDS}", name="valid_prize_vote_kind"),
)

# A flat's house rules. rule_key is the text without capitals, so a flat cannot have the same rule twice.
# It is longer than the text because ignoring capitals can make a few letters longer (ß becomes ss).
house_rules = Table(
    "house_rules",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("flat_id", ForeignKey("flats.id"), nullable=False),
    Column("text", String(MAX_RULE_LENGTH), nullable=False),
    Column("rule_key", String(MAX_RULE_LENGTH * 3), nullable=False),
    Column("added_by", ForeignKey("users.id"), nullable=False),
    Column("added_at", DateTime, nullable=False),
    UniqueConstraint("flat_id", "rule_key", name="one_rule_per_flat"),
)

# Votes to remove a house rule. The primary key means each member can vote once per rule.
rule_removal_votes = Table(
    "rule_removal_votes",
    metadata,
    Column("rule_id", ForeignKey("house_rules.id"), primary_key=True),
    Column("user_id", ForeignKey("users.id"), primary_key=True),
)


def engine_from_url(url: str) -> Engine:
    """Create an engine for a database URL, for example 'sqlite://' in tests."""
    # Supabase gives 'postgresql://...'; SQLAlchemy needs to be told to use psycopg.
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url.removeprefix("postgresql://")
    options = {"connect_args": {"connect_timeout": CONNECT_TIMEOUT_SECONDS}} if url.startswith("postgresql") else {}
    engine = create_engine(url, pool_pre_ping=True, **options)
    if engine.dialect.name == "sqlite":
        # SQLite ignores foreign keys unless they are switched on.
        @event.listens_for(engine, "connect")
        def _foreign_keys_on(connection, _record):
            connection.execute("PRAGMA foreign_keys = ON")

    return engine


def create_tables(engine: Engine) -> None:
    """Create any missing tables and columns. Safe to run on every start."""
    metadata.create_all(engine)
    _add_missing_columns(engine)


def schema() -> tuple:
    """Every table with its column names. Changes whenever a table or column is added in the code."""
    return tuple((table.name, tuple(table.columns.keys())) for table in metadata.sorted_tables)


def _add_missing_columns(engine: Engine) -> None:
    """Add columns that are in the code but not yet in the database, for example a new deadline column.

    create_all() only makes new tables, not new columns in tables that already exist. Only empty-able
    (nullable) columns can be added this way, so the rows already saved stay as they are.
    """
    inspector = inspect(engine)
    for table in metadata.sorted_tables:
        existing = {column["name"] for column in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing:
                continue
            if not column.nullable:
                raise RuntimeError(f"{table.name}.{column.name} is new and not nullable, so it cannot be added.")
            column_type = column.type.compile(dialect=engine.dialect)
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {column.name} {column_type}"))


def get_or_create_user(engine: Engine, email: str, name: str) -> int:
    """Return the id of the user with this email, creating them if needed."""
    email = email.strip().lower()
    name = clean_member_name(name)
    with engine.begin() as conn:
        user_id = conn.scalar(select(users.c.id).where(users.c.email == email))
        if user_id is None:
            user_id = conn.execute(insert(users).values(email=email, name=name)).inserted_primary_key[0]
        return user_id


def get_membership(engine: Engine, user_id: int) -> dict | None:
    """Return the user's flat and role, or None if they are not in a flat."""
    query = (
        select(flats.c.id, flats.c.name, flats.c.invite_code, memberships.c.role)
        .join(memberships, memberships.c.flat_id == flats.c.id)
        .where(memberships.c.user_id == user_id)
    )
    with engine.connect() as conn:
        row = conn.execute(query).mappings().first()
    if row is None:
        return None
    return {"flat_id": row["id"], "flat_name": row["name"], "invite_code": row["invite_code"], "role": row["role"]}


def create_flat(engine: Engine, user_id: int, name: str, make_code=new_invite_code) -> str:
    """Create a flat with the user as admin, and return its invite code."""
    name = clean_flat_name(name)
    if get_membership(engine, user_id) is not None:
        raise ValueError("You are already in a flat.")
    with engine.begin() as conn:
        code = make_code()
        while conn.scalar(select(flats.c.id).where(flats.c.invite_code == code)) is not None:
            code = make_code()
        flat_id = conn.execute(insert(flats).values(name=name, invite_code=code)).inserted_primary_key[0]
        conn.execute(insert(memberships).values(user_id=user_id, flat_id=flat_id, role="admin"))
    return code


def join_flat(engine: Engine, user_id: int, raw_code: str) -> str:
    """Add the user to the flat with this invite code as a member, and return the flat's name."""
    code = clean_invite_code(raw_code)
    if get_membership(engine, user_id) is not None:
        raise ValueError("You are already in a flat.")
    with engine.begin() as conn:
        flat = conn.execute(select(flats.c.id, flats.c.name).where(flats.c.invite_code == code)).first()
        if flat is None:
            raise ValueError("No flat has that invite code.")
        conn.execute(insert(memberships).values(user_id=user_id, flat_id=flat.id, role="member"))
    return flat.name


def list_members(engine: Engine, user_id: int) -> list[dict]:
    """Return the members of the user's own flat, or an empty list if they have none."""
    membership = get_membership(engine, user_id)
    if membership is None:
        return []
    query = (
        select(users.c.name, memberships.c.role)
        .join(memberships, memberships.c.user_id == users.c.id)
        .where(memberships.c.flat_id == membership["flat_id"])
        .order_by(users.c.name)
    )
    with engine.connect() as conn:
        return [dict(row) for row in conn.execute(query).mappings()]


# --- Avatars -----------------------------------------------------------------


def get_avatar(engine: Engine, user_id: int) -> tuple[str, str] | None:
    """Return the user's (emoji, colour), or None if they have not picked an avatar yet."""
    with engine.connect() as conn:
        row = conn.execute(select(users.c.avatar_emoji, users.c.avatar_color).where(users.c.id == user_id)).first()
    if row is None or row.avatar_emoji is None:
        return None
    return row.avatar_emoji, row.avatar_color


def set_avatar(engine: Engine, user_id: int, emoji: str, color: str) -> None:
    """Save the user's own avatar. Only emojis and colours from the lists are accepted."""
    emoji, color = check_avatar(emoji, color)
    with engine.begin() as conn:
        conn.execute(update(users).where(users.c.id == user_id).values(avatar_emoji=emoji, avatar_color=color))


def flat_avatars(engine: Engine, user_id: int) -> dict[str, tuple[str | None, str | None]]:
    """Return {name: (emoji, colour)} for the members of the user's own flat. (None, None): not picked yet."""
    membership = get_membership(engine, user_id)
    if membership is None:
        return {}
    query = (
        select(users.c.name, users.c.avatar_emoji, users.c.avatar_color)
        .join(memberships, memberships.c.user_id == users.c.id)
        .where(memberships.c.flat_id == membership["flat_id"])
    )
    with engine.connect() as conn:
        return {row.name: (row.avatar_emoji, row.avatar_color) for row in conn.execute(query)}


# --- Chores ------------------------------------------------------------------


def _own_flat_id(engine: Engine, user_id: int) -> int:
    """Return the id of the user's own flat, or raise ValueError if they have none."""
    membership = get_membership(engine, user_id)
    if membership is None:
        raise ValueError("You are not in a flat.")
    return membership["flat_id"]


def flat_members(engine: Engine, user_id: int) -> dict[int, str]:
    """Return {user id: name} for the members of the user's own flat."""
    flat_id = _own_flat_id(engine, user_id)
    query = (
        select(users.c.id, users.c.name)
        .join(memberships, memberships.c.user_id == users.c.id)
        .where(memberships.c.flat_id == flat_id)
        .order_by(users.c.name)
    )
    with engine.connect() as conn:
        return {row.id: row.name for row in conn.execute(query)}


def add_chore(
    engine: Engine,
    user_id: int,
    name: str,
    points: float,
    assigned_to: int,
    due_on: date | None = None,
    today: date | None = None,
) -> int:
    """Add a chore to the user's own flat, given to one of its members, and return its id.

    due_on is the deadline, or None for no deadline.
    """
    name = clean_chore_name(name)
    points = clean_points(points)
    due_on = check_deadline(due_on, today or date.today())
    flat_id = _own_flat_id(engine, user_id)
    if assigned_to not in flat_members(engine, user_id):
        raise ValueError("A chore can only be given to a member of your flat.")
    with engine.begin() as conn:
        values = dict(flat_id=flat_id, name=name, points=points, assigned_to=assigned_to, due_on=due_on)
        return conn.execute(insert(chores).values(**values)).inserted_primary_key[0]


def log_chore(engine: Engine, user_id: int, name: str, points: float, now: datetime | None = None) -> int:
    """Save a chore the user has just done themselves ("I took out the trash"), already ticked off."""
    name = clean_chore_name(name)
    points = clean_points(points)
    flat_id = _own_flat_id(engine, user_id)
    with engine.begin() as conn:
        values = dict(flat_id=flat_id, name=name, points=points, assigned_to=user_id, done_at=now or datetime.now())
        return conn.execute(insert(chores).values(**values)).inserted_primary_key[0]


def list_chores(engine: Engine, user_id: int) -> list[dict]:
    """Return the chores of the user's own flat.

    Open chores first, by deadline (soonest first, no deadline last). Then done chores, newest first.
    """
    flat_id = _own_flat_id(engine, user_id)
    with engine.connect() as conn:
        return _chores_on(conn, flat_id)


def _chores_on(conn, flat_id: int) -> list[dict]:
    query = (
        select(
            chores.c.id, chores.c.name, chores.c.points, chores.c.assigned_to, chores.c.done_at, chores.c.due_on,
            users.c.name.label("who"),
        )
        .join(users, users.c.id == chores.c.assigned_to)
        .where(chores.c.flat_id == flat_id)
        .order_by(
            chores.c.done_at.is_not(None),
            chores.c.due_on.is_(None),
            chores.c.due_on,
            chores.c.done_at.desc(),
            chores.c.id,
        )
    )
    rows = conn.execute(query).mappings().all()
    return [{**row, "done": row["done_at"] is not None} for row in rows]


def tick_off_chore(engine: Engine, user_id: int, chore_id: int, now: datetime | None = None) -> None:
    """Mark a chore in the user's own flat as done. Only the person it is given to can do this, once."""
    flat_id = _own_flat_id(engine, user_id)
    with engine.begin() as conn:
        chore = conn.execute(
            select(chores.c.assigned_to, chores.c.done_at).where(chores.c.id == chore_id, chores.c.flat_id == flat_id)
        ).first()
        if chore is None:
            raise ValueError("That chore is not in your flat.")
        check_can_tick_off(chore.assigned_to, chore.done_at is not None, user_id)
        # "done_at IS NULL" stops a double tick if two clicks arrive at the same time.
        result = conn.execute(
            update(chores)
            .where(chores.c.id == chore_id, chores.c.done_at.is_(None))
            .values(done_at=now or datetime.now())
        )
        if result.rowcount != 1:
            raise ValueError("This chore is already done.")


def chores_leaderboard(engine: Engine, user_id: int, today: date | None = None) -> list[tuple[str, int]]:
    """Return (name, points this week) for every member of the user's own flat, highest first."""
    members = flat_members(engine, user_id)
    monday = datetime.combine(week_start(today or date.today()), time.min)
    query = select(chores.c.assigned_to, chores.c.points).where(
        chores.c.flat_id == _own_flat_id(engine, user_id), chores.c.done_at >= monday
    )
    with engine.connect() as conn:
        done = [(row.assigned_to, row.points) for row in conn.execute(query)]
    return leaderboard(members, done)


# --- Shopping ----------------------------------------------------------------


def add_item(engine: Engine, user_id: int, name: str) -> int:
    """Add an item to the user's own flat's shopping list, and return its id."""
    name = clean_item_name(name)
    flat_id = _own_flat_id(engine, user_id)
    with engine.begin() as conn:
        already_there = conn.scalar(
            select(shopping_items.c.id).where(
                shopping_items.c.flat_id == flat_id,
                shopping_items.c.bought_at.is_(None),
                func.lower(shopping_items.c.name) == name.lower(),
            )
        )
        if already_there is not None:
            raise ValueError(f"{name} is already on the list.")
        values = dict(flat_id=flat_id, name=name, added_by=user_id)
        return conn.execute(insert(shopping_items).values(**values)).inserted_primary_key[0]


def list_items(engine: Engine, user_id: int) -> list[dict]:
    """Return the shopping list of the user's own flat: items still to buy first, then bought ones."""
    flat_id = _own_flat_id(engine, user_id)
    with engine.connect() as conn:
        return _items_on(conn, flat_id)


def _items_on(conn, flat_id: int) -> list[dict]:
    buyer = users.alias("buyer")
    query = (
        select(shopping_items.c.id, shopping_items.c.name, shopping_items.c.bought_at, buyer.c.name.label("bought_by"))
        .outerjoin(buyer, buyer.c.id == shopping_items.c.bought_by)
        .where(shopping_items.c.flat_id == flat_id)
        .order_by(shopping_items.c.bought_at.is_not(None), shopping_items.c.id)
    )
    rows = conn.execute(query).mappings().all()
    return [{**row, "bought": row["bought_at"] is not None} for row in rows]


def mark_bought(engine: Engine, user_id: int, item_id: int, now: datetime | None = None) -> None:
    """Mark an item on the user's own flat's list as bought by them."""
    flat_id = _own_flat_id(engine, user_id)
    with engine.begin() as conn:
        # "bought_at IS NULL" also stops a double click from buying it twice.
        result = conn.execute(
            update(shopping_items)
            .where(
                shopping_items.c.id == item_id,
                shopping_items.c.flat_id == flat_id,
                shopping_items.c.bought_at.is_(None),
            )
            .values(bought_by=user_id, bought_at=now or datetime.now())
        )
    if result.rowcount != 1:
        raise ValueError("That item is not on your list, or it is already bought.")


def remove_item(engine: Engine, user_id: int, item_id: int) -> None:
    """Remove one item from the user's own flat's list."""
    flat_id = _own_flat_id(engine, user_id)
    with engine.begin() as conn:
        result = conn.execute(
            delete(shopping_items).where(shopping_items.c.id == item_id, shopping_items.c.flat_id == flat_id)
        )
    if result.rowcount != 1:
        raise ValueError("That item is not on your list.")


def clear_bought_items(engine: Engine, user_id: int) -> int:
    """Remove all bought items from the user's own flat's list, and return how many were removed."""
    flat_id = _own_flat_id(engine, user_id)
    with engine.begin() as conn:
        result = conn.execute(
            delete(shopping_items).where(shopping_items.c.flat_id == flat_id, shopping_items.c.bought_at.is_not(None))
        )
    return result.rowcount


def add_expense(engine: Engine, user_id: int, amount, description: str, now: datetime | None = None) -> None:
    """Save a shared cost that this user paid. It is split equally between their flat."""
    cents = cost_to_cents(amount)
    description = clean_description(description)
    flat_id = _own_flat_id(engine, user_id)
    values = dict(
        flat_id=flat_id, paid_by=user_id, amount_cents=cents, description=description, created_at=now or datetime.now()
    )
    with engine.begin() as conn:
        conn.execute(insert(expenses).values(**values))


def confirm_payment(engine: Engine, user_id: int, from_user: int, amount, now: datetime | None = None) -> None:
    """Save that from_user paid this user back. Only the person who got the money can confirm it."""
    cents = cost_to_cents(amount)
    flat_id = _own_flat_id(engine, user_id)
    check_payment(payer=from_user, receiver=user_id, confirmed_by=user_id, members=list(flat_members(engine, user_id)))
    values = dict(
        flat_id=flat_id, from_user=from_user, to_user=user_id, amount_cents=cents, created_at=now or datetime.now()
    )
    with engine.begin() as conn:
        conn.execute(insert(payments).values(**values))


def money_overview(engine: Engine, user_id: int) -> dict:
    """Return the costs, payments, balances and settle-up suggestions of the user's own flat.

    mine: the user's own balance in cents. mine_to_pay and mine_to_get: [(name, cents)] for the user.
    balances: [(name, cents)] by name. settle_up: [(payer name, receiver name, cents)].
    expenses and payments: newest first.
    """
    flat_id = _own_flat_id(engine, user_id)
    members = flat_members(engine, user_id)
    payer, receiver = users.alias("payer"), users.alias("receiver")
    with engine.connect() as conn:
        expense_rows = conn.execute(
            select(expenses, users.c.name.label("who"))
            .join(users, users.c.id == expenses.c.paid_by)
            .where(expenses.c.flat_id == flat_id)
            .order_by(expenses.c.created_at.desc(), expenses.c.id.desc())
        ).mappings().all()
        payment_rows = conn.execute(
            select(payments, payer.c.name.label("from_name"), receiver.c.name.label("to_name"))
            .join(payer, payer.c.id == payments.c.from_user)
            .join(receiver, receiver.c.id == payments.c.to_user)
            .where(payments.c.flat_id == flat_id)
            .order_by(payments.c.created_at.desc(), payments.c.id.desc())
        ).mappings().all()
    balance = shopping_balances(
        list(members),
        [(row["paid_by"], row["amount_cents"]) for row in expense_rows],
        [(row["from_user"], row["to_user"], row["amount_cents"]) for row in payment_rows],
    )
    transfers = settle_up(balance)
    return {
        "mine": balance[user_id],
        "mine_to_pay": [(members[to], cents) for payer_id, to, cents in transfers if payer_id == user_id],
        "mine_to_get": [(members[frm], cents) for frm, receiver_id, cents in transfers if receiver_id == user_id],
        "balances": [(members[member], balance[member]) for member in members],
        "settle_up": [(members[a], members[b], cents) for a, b, cents in transfers],
        "expenses": [
            {"who": r["who"], "cents": r["amount_cents"], "description": r["description"], "at": r["created_at"]}
            for r in expense_rows
        ],
        "payments": [
            {"from": r["from_name"], "to": r["to_name"], "cents": r["amount_cents"], "at": r["created_at"]}
            for r in payment_rows
        ],
    }


# --- Fund --------------------------------------------------------------------


def _own_admin_flat_id(engine: Engine, user_id: int) -> int:
    """Return the id of the user's own flat, or raise ValueError unless they are its admin."""
    membership = get_membership(engine, user_id)
    if membership is None:
        raise ValueError("You are not in a flat.")
    if membership["role"] != "admin":
        raise ValueError("Only the admin can do this.")
    return membership["flat_id"]


def _balance(conn, flat_id: int) -> int:
    return conn.scalar(select(func.coalesce(func.sum(fund_entries.c.cents), 0)).where(fund_entries.c.flat_id == flat_id))


def add_pant(engine: Engine, user_id: int, amount: float, now: datetime | None = None) -> None:
    """Add pant money from this user to their own flat's fund."""
    cents = to_cents(amount)
    flat_id = _own_flat_id(engine, user_id)
    with engine.begin() as conn:
        conn.execute(insert(fund_entries).values(
            flat_id=flat_id, user_id=user_id, what="Pant", cents=cents, created_at=now or datetime.now()))


def take_out(engine: Engine, user_id: int, what: str, amount: float, now: datetime | None = None) -> None:
    """Take money out of the fund for a shared cost. Only the admin can, and never below zero."""
    what = clean_description(what)
    cents = to_cents(amount)
    flat_id = _own_admin_flat_id(engine, user_id)
    with engine.begin() as conn:
        # Lock the flat's row, so two withdrawals at the same time cannot both pass the check.
        conn.execute(select(flats.c.id).where(flats.c.id == flat_id).with_for_update())
        check_can_take_out(_balance(conn, flat_id), cents)
        conn.execute(insert(fund_entries).values(
            flat_id=flat_id, user_id=user_id, what=what, cents=-cents, created_at=now or datetime.now()))


def fund_balance(engine: Engine, user_id: int) -> int:
    """Return the balance of the user's own flat's fund, in cents."""
    flat_id = _own_flat_id(engine, user_id)
    with engine.connect() as conn:
        return _balance(conn, flat_id)


def fund_history(engine: Engine, user_id: int) -> list[dict]:
    """Return every entry in the user's own flat's fund, newest first."""
    flat_id = _own_flat_id(engine, user_id)
    query = (
        select(fund_entries.c.created_at, fund_entries.c.what, fund_entries.c.cents, users.c.name)
        .join(users, users.c.id == fund_entries.c.user_id)
        .where(fund_entries.c.flat_id == flat_id)
        .order_by(fund_entries.c.created_at.desc(), fund_entries.c.id.desc())
    )
    with engine.connect() as conn:
        return [
            {"date": row.created_at.date(), "what": row.what, "who": row.name, "cents": row.cents}
            for row in conn.execute(query)
        ]


def set_fund_goal(engine: Engine, user_id: int, name: str, amount: float) -> None:
    """Set (or replace) the savings goal of the user's own flat. Only the admin can."""
    name = clean_description(name)
    cents = to_cents(amount)
    flat_id = _own_admin_flat_id(engine, user_id)
    with engine.begin() as conn:
        conn.execute(delete(fund_goals).where(fund_goals.c.flat_id == flat_id))
        conn.execute(insert(fund_goals).values(flat_id=flat_id, name=name, cents=cents))


def get_fund_goal(engine: Engine, user_id: int) -> dict | None:
    """Return the savings goal of the user's own flat as {'name', 'cents'}, or None."""
    flat_id = _own_flat_id(engine, user_id)
    with engine.connect() as conn:
        row = conn.execute(select(fund_goals.c.name, fund_goals.c.cents).where(fund_goals.c.flat_id == flat_id)).first()
    return None if row is None else {"name": row.name, "cents": row.cents}


# --- House rules (specs/house-rules.md) -----------------------------------------


def add_rule(engine: Engine, user_id: int, raw: str, now: datetime | None = None) -> int:
    """Add a rule to the user's own flat, and return its id."""
    flat_id = _own_flat_id(engine, user_id)
    try:
        with engine.begin() as conn:
            existing = list(conn.scalars(select(house_rules.c.text).where(house_rules.c.flat_id == flat_id)))
            rule = clean_rule(raw, existing)
            values = dict(flat_id=flat_id, text=rule, rule_key=rule_key(rule), added_by=user_id, added_at=now or datetime.now())
            return conn.execute(insert(house_rules).values(**values)).inserted_primary_key[0]
    except IntegrityError as error:  # A flatmate added the same rule at the same moment.
        raise ValueError("That rule is already on the list.") from error


def list_rules(engine: Engine, user_id: int) -> list[dict]:
    """Return the rules of the user's own flat, oldest first, with who voted to remove each one."""
    flat_id = _own_flat_id(engine, user_id)
    rules_query = (
        select(house_rules.c.id, house_rules.c.text, house_rules.c.added_at, users.c.name.label("who"))
        .join(users, users.c.id == house_rules.c.added_by)
        .where(house_rules.c.flat_id == flat_id)
        .order_by(house_rules.c.id)
    )
    votes_query = (
        select(rule_removal_votes.c.rule_id, users.c.id, users.c.name)
        .join(users, users.c.id == rule_removal_votes.c.user_id)
        .join(house_rules, house_rules.c.id == rule_removal_votes.c.rule_id)
        .where(house_rules.c.flat_id == flat_id)
        .order_by(users.c.name)
    )
    members_query = select(func.count()).select_from(memberships).where(memberships.c.flat_id == flat_id)
    with engine.connect() as conn:
        rules = conn.execute(rules_query).mappings().all()
        votes = conn.execute(votes_query).all()
        needed = votes_needed(conn.scalar(members_query))
    return [
        {
            **rule,
            "voters": [vote.name for vote in votes if vote.rule_id == rule["id"]],
            "voter_ids": [vote.id for vote in votes if vote.rule_id == rule["id"]],
            "votes_needed": needed,
        }
        for rule in rules
    ]


def vote_to_remove(engine: Engine, user_id: int, rule_id: int) -> bool:
    """Vote to remove a rule of the user's own flat. Return True if this vote reached the majority and removed it."""
    flat_id = _own_flat_id(engine, user_id)
    try:
        with engine.begin() as conn:
            # Lock the rule, so two votes at the same moment are counted one after the other.
            found = conn.scalar(
                select(house_rules.c.id)
                .where(house_rules.c.id == rule_id, house_rules.c.flat_id == flat_id)
                .with_for_update()
            )
            if found is None:
                raise ValueError("That rule is not on your list.")
            voters = list(conn.scalars(select(rule_removal_votes.c.user_id).where(rule_removal_votes.c.rule_id == rule_id)))
            check_can_vote_to_remove(voters, user_id)
            conn.execute(insert(rule_removal_votes).values(rule_id=rule_id, user_id=user_id))
            members = conn.scalar(select(func.count()).select_from(memberships).where(memberships.c.flat_id == flat_id))
            if not has_majority(len(voters) + 1, members):
                return False
            conn.execute(delete(rule_removal_votes).where(rule_removal_votes.c.rule_id == rule_id))
            conn.execute(delete(house_rules).where(house_rules.c.id == rule_id))
            return True
    except IntegrityError as error:  # The same member voted twice at the same moment.
        raise ValueError("You already voted to remove this rule.") from error


# --- Activities (specs/activities.md) -------------------------------------------


def add_activity(
    engine: Engine, user_id: int, name: str, cost, planned_on: date | None,
    today: date | None = None, now: datetime | None = None,
) -> int:
    """Add an activity to the user's own flat, and return its id."""
    flat_id = _own_flat_id(engine, user_id)
    check_activity_date(planned_on, today or date.today())
    cost_cents = activity_cost_cents(cost)
    try:
        with engine.begin() as conn:
            existing = list(conn.scalars(select(activities.c.name).where(activities.c.flat_id == flat_id)))
            clean = clean_activity_name(name, existing)
            values = dict(
                flat_id=flat_id, name=clean, name_key=activity_key(clean), cost_cents=cost_cents,
                planned_on=planned_on, added_by=user_id, created_at=now or datetime.now(),
            )
            return conn.execute(insert(activities).values(**values)).inserted_primary_key[0]
    except IntegrityError as error:  # A flatmate added the same activity at the same moment.
        raise ValueError(f"{' '.join(name.split())} is already on the list.") from error


def list_activities(engine: Engine, user_id: int) -> list[dict]:
    """Return the activities of the user's own flat, most votes first, each with its votes.

    Each activity has 'id', 'activity' (its name), 'cost_cents', 'planned_on', 'added_by', 'who' (who added it)
    and 'votes': [{'user_id', 'name', 'day'}] in the order they were cast.
    """
    flat_id = _own_flat_id(engine, user_id)
    with engine.connect() as conn:
        return _activities_on(conn, flat_id)


def _activities_on(conn, flat_id: int) -> list[dict]:
    """The flat's activities with their votes, in one query, most votes first."""
    adder, voter = users.alias("adder"), users.alias("voter")
    query = (
        select(
            activities.c.id, activities.c.name, activities.c.cost_cents, activities.c.planned_on,
            activities.c.added_by, adder.c.name.label("who"), activity_votes.c.user_id.label("voter_id"),
            activity_votes.c.voted_on, voter.c.name.label("voter_name"),
        )
        .join(adder, adder.c.id == activities.c.added_by)
        .outerjoin(activity_votes, activity_votes.c.activity_id == activities.c.id)
        .outerjoin(voter, voter.c.id == activity_votes.c.user_id)
        .where(activities.c.flat_id == flat_id)
        .order_by(activities.c.id, activity_votes.c.voted_on, voter.c.name)
    )
    items: dict[int, dict] = {}
    for row in conn.execute(query):
        item = items.setdefault(row.id, {
            "id": row.id, "activity": row.name, "cost_cents": row.cost_cents, "planned_on": row.planned_on,
            "added_by": row.added_by, "who": row.who, "votes": [],
        })
        if row.voter_id is not None:
            item["votes"].append({"user_id": row.voter_id, "name": row.voter_name, "day": row.voted_on})
    ranking_votes = [
        {"activity": item["activity"], "who": vote["user_id"]} for item in items.values() for vote in item["votes"]
    ]
    return [item for item, _ in rank_activities(list(items.values()), ranking_votes)]


def vote_for_activity(engine: Engine, user_id: int, activity_id: int, today: date | None = None) -> None:
    """Vote for an activity of the user's own flat: once per activity and once per day."""
    flat_id = _own_flat_id(engine, user_id)
    today = today or date.today()
    try:
        with engine.begin() as conn:
            # Lock the activity, so it cannot be removed while this vote is being saved.
            name = conn.scalar(
                select(activities.c.name)
                .where(activities.c.id == activity_id, activities.c.flat_id == flat_id)
                .with_for_update()
            )
            if name is None:
                raise ValueError("That activity is not on your list.")
            mine = conn.execute(
                select(activities.c.name, activity_votes.c.voted_on)
                .join(activities, activities.c.id == activity_votes.c.activity_id)
                .where(activity_votes.c.user_id == user_id)
            ).all()
            votes = [{"activity": row.name, "who": user_id, "day": row.voted_on} for row in mine]
            check_can_vote([name] + [row.name for row in mine], votes, name, user_id, today)
            conn.execute(insert(activity_votes).values(activity_id=activity_id, user_id=user_id, voted_on=today))
    except IntegrityError as error:  # Two votes at the same moment: the database lets only one through.
        raise ValueError("You already voted for this activity or today.") from error


def remove_activity(engine: Engine, user_id: int, activity_id: int) -> None:
    """Remove an activity and its votes, if the user added it or is the admin of its flat."""
    membership = get_membership(engine, user_id)
    if membership is None:
        raise ValueError("You are not in a flat.")
    with engine.begin() as conn:
        added_by = conn.scalar(
            select(activities.c.added_by)
            .where(activities.c.id == activity_id, activities.c.flat_id == membership["flat_id"])
            .with_for_update()
        )
        if added_by is None:
            raise ValueError("That activity is not on your list.")
        check_can_remove_activity(added_by, user_id, membership["role"])
        conn.execute(delete(activity_votes).where(activity_votes.c.activity_id == activity_id))
        conn.execute(delete(activities).where(activities.c.id == activity_id))


# --- One visit for the Today tab (specs/speed.md) --------------------------------


def member_context(engine: Engine, user_id: int) -> dict:
    """Return the user's 'avatar' and 'membership' (as get_avatar and get_membership) in one query."""
    query = (
        select(
            users.c.avatar_emoji, users.c.avatar_color, memberships.c.role, memberships.c.flat_id,
            flats.c.name.label("flat_name"), flats.c.invite_code,
        )
        .select_from(
            users.outerjoin(memberships, memberships.c.user_id == users.c.id)
            .outerjoin(flats, flats.c.id == memberships.c.flat_id)
        )
        .where(users.c.id == user_id)
    )
    with engine.connect() as conn:
        row = conn.execute(query).first()
    if row is None:
        return {"avatar": None, "membership": None}
    avatar = None if row.avatar_emoji is None else (row.avatar_emoji, row.avatar_color)
    membership = None if row.flat_id is None else {
        "flat_id": row.flat_id, "flat_name": row.flat_name, "invite_code": row.invite_code, "role": row.role,
    }
    return {"avatar": avatar, "membership": membership}


def today_overview(engine: Engine, user_id: int, today: date | None = None) -> dict:
    """Return everything the Today tab shows, over one connection and at most 7 queries.

    The database is far from the app, so each trip counts. The flat is found from the user's id.
    """
    own_flat = select(memberships.c.flat_id).where(memberships.c.user_id == user_id).scalar_subquery()
    members_query = (
        select(
            users.c.id, users.c.name, users.c.avatar_emoji, users.c.avatar_color,
            memberships.c.role, memberships.c.flat_id,
            # The fund comes along with the members, to save a trip to the database.
            select(func.coalesce(func.sum(fund_entries.c.cents), 0))
            .where(fund_entries.c.flat_id == memberships.c.flat_id)
            .correlate(memberships).scalar_subquery().label("balance"),
            select(fund_goals.c.name).where(fund_goals.c.flat_id == memberships.c.flat_id)
            .correlate(memberships).scalar_subquery().label("goal_name"),
            select(fund_goals.c.cents).where(fund_goals.c.flat_id == memberships.c.flat_id)
            .correlate(memberships).scalar_subquery().label("goal_cents"),
        )
        .join(memberships, memberships.c.user_id == users.c.id)
        .where(memberships.c.flat_id == own_flat)
        .order_by(users.c.name)
    )
    monday_of_week = week_start(today or date.today())
    with engine.connect() as conn:
        member_rows = conn.execute(members_query).all()
        if not member_rows:
            raise ValueError("You are not in a flat.")
        flat_id = member_rows[0].flat_id
        chore_rows = _chores_on(conn, flat_id)
        money_rows = conn.execute(
            union_all(
                select(expenses.c.paid_by.label("payer"), null().label("receiver"), expenses.c.amount_cents.label("cents"))
                .where(expenses.c.flat_id == flat_id),
                select(payments.c.from_user, payments.c.to_user, payments.c.amount_cents)
                .where(payments.c.flat_id == flat_id),
            )
        ).all()
        items = _items_on(conn, flat_id)
        activity_items = _activities_on(conn, flat_id)
        prize_options, rules_in_vote = _open_votes_on(conn, flat_id, monday_of_week)

    fund_row = member_rows[0]
    names = {row.id: row.name for row in member_rows}
    balance = shopping_balances(
        list(names),
        [(row.payer, row.cents) for row in money_rows if row.receiver is None],
        [(row.payer, row.receiver, row.cents) for row in money_rows if row.receiver is not None],
    )
    transfers = settle_up(balance)
    monday = datetime.combine(week_start(today or date.today()), time.min)
    done_this_week = [(c["assigned_to"], c["points"]) for c in chore_rows if c["done"] and c["done_at"] >= monday]
    return {
        "my_name": names[user_id],
        "members": [{"id": row.id, "name": row.name, "role": row.role} for row in member_rows],
        "avatars": {row.name: (row.avatar_emoji, row.avatar_color) for row in member_rows},
        "chores": chore_rows,
        "money": {
            "mine": balance[user_id],
            "mine_to_pay": [(names[to], cents) for payer, to, cents in transfers if payer == user_id],
            "mine_to_get": [(names[frm], cents) for frm, to, cents in transfers if to == user_id],
        },
        "items": items,
        "fund": fund_row.balance,
        "goal": None if fund_row.goal_name is None else {"name": fund_row.goal_name, "cents": fund_row.goal_cents},
        "leaderboard": leaderboard(names, done_this_week),
        "activities": activity_items,
        "prize_options": prize_options,
        "rules_in_vote": rules_in_vote,
        "votes_needed": votes_needed(len(member_rows)),
    }


def _open_votes_on(conn, flat_id: int, monday: date) -> tuple[dict, list[dict]]:
    """This week's prize options, and the rules someone has voted to remove, with their votes, in one query."""
    prize_part = (
        select(
            literal_column("'prize'").label("source"), weekly_prizes.c.id, weekly_prizes.c.kind,
            weekly_prizes.c.name, weekly_prize_votes.c.user_id.label("voter_id"), users.c.name.label("voter_name"),
        )
        .select_from(
            weekly_prizes.outerjoin(weekly_prize_votes, weekly_prize_votes.c.prize_id == weekly_prizes.c.id)
            .outerjoin(users, users.c.id == weekly_prize_votes.c.user_id)
        )
        .where(weekly_prizes.c.flat_id == flat_id, weekly_prizes.c.week_start == monday)
    )
    rule_part = (
        select(
            literal_column("'rule'"), house_rules.c.id, null(), house_rules.c.text,
            rule_removal_votes.c.user_id, users.c.name,
        )
        .join(rule_removal_votes, rule_removal_votes.c.rule_id == house_rules.c.id)
        .join(users, users.c.id == rule_removal_votes.c.user_id)
        .where(house_rules.c.flat_id == flat_id)
    )
    rows = sorted(conn.execute(union_all(prize_part, rule_part)).all(), key=lambda row: (row.id, row.voter_name or ""))

    prizes: dict[int, dict] = {}
    rules: dict[int, dict] = {}
    for row in rows:
        if row.source == "prize":
            option = prizes.setdefault(row.id, {"id": row.id, "kind": row.kind, "name": row.name, "votes": []})
            if row.voter_id is not None:
                option["votes"].append({"user_id": row.voter_id, "name": row.voter_name})
        else:
            rule = rules.setdefault(row.id, {"id": row.id, "text": row.name, "voters": [], "voter_ids": []})
            rule["voters"].append(row.voter_name)
            rule["voter_ids"].append(row.voter_id)
    options = {kind: [o for o in prizes.values() if o["kind"] == kind] for kind in PRIZE_KINDS}
    return options, list(rules.values())


# --- Weekly prize (specs/weekly-prize.md) ----------------------------------------


def add_prize(
    engine: Engine, user_id: int, kind: str, raw: str, today: date | None = None, now: datetime | None = None
) -> int:
    """Suggest what this week's winner gets or loser has to do, and return the option's id."""
    flat_id = _own_flat_id(engine, user_id)
    today = today or date.today()
    monday = week_start(today)
    try:
        with engine.begin() as conn:
            existing = list(conn.scalars(
                select(weekly_prizes.c.name).where(
                    weekly_prizes.c.flat_id == flat_id,
                    weekly_prizes.c.week_start == monday,
                    weekly_prizes.c.kind == kind,
                )
            ))
            check_can_suggest_prize(kind, len(existing), today)
            name = clean_prize(raw, existing)
            values = dict(
                flat_id=flat_id, week_start=monday, kind=kind, name=name, name_key=prize_key(name),
                added_by=user_id, created_at=now or datetime.now(),
            )
            return conn.execute(insert(weekly_prizes).values(**values)).inserted_primary_key[0]
    except IntegrityError as error:  # A flatmate suggested the same thing at the same moment.
        raise ValueError("That has already been suggested this week.") from error


def vote_prize(engine: Engine, user_id: int, prize_id: int, today: date | None = None) -> None:
    """Vote for an option of the user's own flat: one vote per member in each vote, each week."""
    flat_id = _own_flat_id(engine, user_id)
    today = today or date.today()
    try:
        with engine.begin() as conn:
            prize = conn.execute(
                select(weekly_prizes.c.week_start, weekly_prizes.c.kind)
                .where(weekly_prizes.c.id == prize_id, weekly_prizes.c.flat_id == flat_id)
            ).first()
            if prize is None:
                raise ValueError("That option is not on your list.")
            already = conn.scalar(
                select(weekly_prize_votes.c.prize_id).where(
                    weekly_prize_votes.c.user_id == user_id,
                    weekly_prize_votes.c.week_start == prize.week_start,
                    weekly_prize_votes.c.kind == prize.kind,
                )
            )
            check_can_vote_prize(prize.week_start, already is not None, today)
            conn.execute(insert(weekly_prize_votes).values(
                user_id=user_id, week_start=prize.week_start, kind=prize.kind, prize_id=prize_id,
            ))
    except IntegrityError as error:  # Two votes at the same moment: the database lets only one through.
        raise ValueError("You already voted in this vote this week.") from error


def prize_overview(engine: Engine, user_id: int, today: date | None = None) -> dict:
    """Return this week's options and deal, and last week's result, for the user's own flat, in one visit."""
    today = today or date.today()
    monday = week_start(today)
    last_monday = monday - timedelta(days=7)
    own_flat = select(memberships.c.flat_id).where(memberships.c.user_id == user_id).scalar_subquery()
    adder, voter = users.alias("adder"), users.alias("voter")
    with engine.connect() as conn:
        member_rows = conn.execute(
            select(users.c.id, users.c.name, memberships.c.flat_id)
            .join(memberships, memberships.c.user_id == users.c.id)
            .where(memberships.c.flat_id == own_flat)
            .order_by(users.c.name)
        ).all()
        if not member_rows:
            raise ValueError("You are not in a flat.")
        flat_id = member_rows[0].flat_id
        prize_rows = conn.execute(
            select(
                weekly_prizes.c.id, weekly_prizes.c.week_start, weekly_prizes.c.kind, weekly_prizes.c.name,
                adder.c.name.label("who"), weekly_prize_votes.c.user_id.label("voter_id"),
                voter.c.name.label("voter_name"),
            )
            .join(adder, adder.c.id == weekly_prizes.c.added_by)
            .outerjoin(weekly_prize_votes, weekly_prize_votes.c.prize_id == weekly_prizes.c.id)
            .outerjoin(voter, voter.c.id == weekly_prize_votes.c.user_id)
            .where(weekly_prizes.c.flat_id == flat_id, weekly_prizes.c.week_start.in_((last_monday, monday)))
            .order_by(weekly_prizes.c.id, voter.c.name)
        ).all()
        done_rows = conn.execute(
            select(chores.c.assigned_to, chores.c.points).where(
                chores.c.flat_id == flat_id,
                chores.c.done_at >= datetime.combine(last_monday, time.min),
                chores.c.done_at < datetime.combine(monday, time.min),
            )
        ).all()

    options: dict[int, dict] = {}
    for row in prize_rows:
        option = options.setdefault(row.id, {
            "id": row.id, "week": row.week_start, "kind": row.kind, "name": row.name, "who": row.who, "votes": [],
        })
        if row.voter_id is not None:
            option["votes"].append({"user_id": row.voter_id, "name": row.voter_name})

    def of(week: date, kind: str) -> list[dict]:
        found = [o for o in options.values() if o["week"] == week and o["kind"] == kind]
        return sorted(found, key=lambda o: (-len(o["votes"]), o["id"]))

    def prize_name(week: date, kind: str) -> str | None:
        chosen = chosen_prize(of(week, kind))
        return chosen["name"] if chosen else None

    names = {row.id: row.name for row in member_rows}
    result = week_result(leaderboard(names, [(row.assigned_to, row.points) for row in done_rows]))
    return {
        "week": monday,
        "voting_open": voting_is_open(today),
        "options": {kind: of(monday, kind) for kind in PRIZE_KINDS},
        "chosen": {kind: chosen_prize(of(monday, kind)) for kind in PRIZE_KINDS},
        "last_week": {
            **result,
            "winner_prize": prize_name(last_monday, "winner"),
            "loser_prize": prize_name(last_monday, "loser"),
        },
    }
