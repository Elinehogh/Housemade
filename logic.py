"""The rules of the app. Pure functions only: no Streamlit and no database here."""

MAX_NAME_LENGTH = 30


def clean_member_name(raw: str) -> str:
    """Return a tidy member name, or raise ValueError if it is not allowed."""
    name = " ".join(raw.split())
    if not name:
        raise ValueError("Name cannot be empty.")
    if len(name) > MAX_NAME_LENGTH:
        raise ValueError(f"Name can be at most {MAX_NAME_LENGTH} characters.")
    return name
