"""Storage. Every read and write of saved data goes through this file.

The deployed app uses a hosted Postgres database (Supabase). Tests and local
runs without a secret use SQLite. Both are reached through SQLAlchemy, so the
functions below work the same on either.

Access control: functions that read or change a flat's data take the user's
id, not a flat id, and look up the user's own flat. A user can never reach
another flat's data by passing a different id.
"""

from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    event,
    insert,
    select,
)
from sqlalchemy.engine import Engine

from logic import (
    INVITE_CODE_LENGTH,
    MAX_FLAT_NAME_LENGTH,
    MAX_NAME_LENGTH,
    ROLES,
    clean_flat_name,
    clean_invite_code,
    clean_member_name,
    new_invite_code,
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


def engine_from_url(url: str) -> Engine:
    """Create an engine for a database URL, for example 'sqlite://' in tests."""
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
