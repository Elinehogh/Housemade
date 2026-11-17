"""Storage. Every read and write of saved data goes through this file.

The deployed app uses a hosted Postgres database (Supabase). Tests and local
runs without a secret use SQLite. Both are reached through SQLAlchemy, so the
functions below work the same on either.

Access control: functions that read or change a flat's data take the user's
id, not a flat id, and look up the user's own flat. A user can never reach
another flat's data by passing a different id.
"""

from datetime import date, datetime, time

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    delete,
    event,
    func,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Engine

from logic import (
    INVITE_CODE_LENGTH,
    MAX_AMOUNT_CENTS,
    MAX_CHORE_LENGTH,
    MAX_DESCRIPTION_LENGTH,
    MAX_FLAT_NAME_LENGTH,
    MAX_ITEM_LENGTH,
    MAX_NAME_LENGTH,
    MAX_POINTS,
    MIN_POINTS,
    ROLES,
    check_can_tick_off,
    check_payment,
    clean_chore_name,
    clean_description,
    clean_flat_name,
    clean_invite_code,
    clean_item_name,
    clean_member_name,
    clean_points,
    leaderboard,
    new_invite_code,
    settle_up,
    shopping_balances,
    to_cents,
    week_start,
)

metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("email", String(254), nullable=False, unique=True),
    Column("name", String(MAX_NAME_LENGTH), nullable=False),
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
chores = Table(
    "chores",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("flat_id", ForeignKey("flats.id"), nullable=False),
    Column("name", String(MAX_CHORE_LENGTH), nullable=False),
    Column("points", Integer, nullable=False),
    Column("assigned_to", ForeignKey("users.id"), nullable=False),
    Column("done_at", DateTime, nullable=True),
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


def engine_from_url(url: str) -> Engine:
    """Create an engine for a database URL, for example 'sqlite://' in tests."""
    # Supabase gives 'postgresql://...'; SQLAlchemy needs to be told to use psycopg.
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url.removeprefix("postgresql://")
    engine = create_engine(url, pool_pre_ping=True)
    if engine.dialect.name == "sqlite":
        # SQLite ignores foreign keys unless they are switched on.
        @event.listens_for(engine, "connect")
        def _foreign_keys_on(connection, _record):
            connection.execute("PRAGMA foreign_keys = ON")

    return engine


def create_tables(engine: Engine) -> None:
    """Create any missing tables. Safe to run on every start."""
    metadata.create_all(engine)


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


def add_chore(engine: Engine, user_id: int, name: str, points: float, assigned_to: int) -> int:
    """Add a chore to the user's own flat, given to one of its members, and return its id."""
    name = clean_chore_name(name)
    points = clean_points(points)
    flat_id = _own_flat_id(engine, user_id)
    if assigned_to not in flat_members(engine, user_id):
        raise ValueError("A chore can only be given to a member of your flat.")
    with engine.begin() as conn:
        values = dict(flat_id=flat_id, name=name, points=points, assigned_to=assigned_to)
        return conn.execute(insert(chores).values(**values)).inserted_primary_key[0]


def list_chores(engine: Engine, user_id: int) -> list[dict]:
    """Return the chores of the user's own flat: open ones first, then the oldest first."""
    flat_id = _own_flat_id(engine, user_id)
    query = (
        select(chores.c.id, chores.c.name, chores.c.points, chores.c.assigned_to, chores.c.done_at, users.c.name.label("who"))
        .join(users, users.c.id == chores.c.assigned_to)
        .where(chores.c.flat_id == flat_id)
        .order_by(chores.c.done_at.is_not(None), chores.c.id)
    )
    with engine.connect() as conn:
        rows = conn.execute(query).mappings().all()
    return [
        {"id": r["id"], "name": r["name"], "points": r["points"], "assigned_to": r["assigned_to"],
         "who": r["who"], "done": r["done_at"] is not None}
        for r in rows
    ]


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
    buyer = users.alias("buyer")
    query = (
        select(shopping_items.c.id, shopping_items.c.name, shopping_items.c.bought_at, buyer.c.name.label("bought_by"))
        .outerjoin(buyer, buyer.c.id == shopping_items.c.bought_by)
        .where(shopping_items.c.flat_id == flat_id)
        .order_by(shopping_items.c.bought_at.is_not(None), shopping_items.c.id)
    )
    with engine.connect() as conn:
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
    cents = to_cents(amount)
    description = clean_description(description)
    flat_id = _own_flat_id(engine, user_id)
    values = dict(
        flat_id=flat_id, paid_by=user_id, amount_cents=cents, description=description, created_at=now or datetime.now()
    )
    with engine.begin() as conn:
        conn.execute(insert(expenses).values(**values))


def confirm_payment(engine: Engine, user_id: int, from_user: int, amount, now: datetime | None = None) -> None:
    """Save that from_user paid this user back. Only the person who got the money can confirm it."""
    cents = to_cents(amount)
    flat_id = _own_flat_id(engine, user_id)
    check_payment(payer=from_user, receiver=user_id, confirmed_by=user_id, members=list(flat_members(engine, user_id)))
    values = dict(
        flat_id=flat_id, from_user=from_user, to_user=user_id, amount_cents=cents, created_at=now or datetime.now()
    )
    with engine.begin() as conn:
        conn.execute(insert(payments).values(**values))


def money_overview(engine: Engine, user_id: int) -> dict:
    """Return the costs, payments, balances and settle-up suggestions of the user's own flat.

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
    return {
        "balances": [(members[member], balance[member]) for member in members],
        "settle_up": [(members[a], members[b], cents) for a, b, cents in settle_up(balance)],
        "expenses": [
            {"who": r["who"], "cents": r["amount_cents"], "description": r["description"], "at": r["created_at"]}
            for r in expense_rows
        ],
        "payments": [
            {"from": r["from_name"], "to": r["to_name"], "cents": r["amount_cents"], "at": r["created_at"]}
            for r in payment_rows
        ],
    }
