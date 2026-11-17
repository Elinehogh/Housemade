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
    event,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Engine

from logic import (
    INVITE_CODE_LENGTH,
    MAX_CHORE_LENGTH,
    MAX_FLAT_NAME_LENGTH,
    MAX_NAME_LENGTH,
    MAX_POINTS,
    MIN_POINTS,
    ROLES,
    check_can_tick_off,
    clean_chore_name,
    clean_flat_name,
    clean_invite_code,
    clean_member_name,
    clean_points,
    leaderboard,
    new_invite_code,
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
