"""A friendly message instead of a technical error when the database cannot be reached (specs/reliability.md)."""

import logging
from contextlib import contextmanager

import streamlit as st
from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError

DATABASE_MESSAGE = "Housemade can't reach the database right now. What you saved is safe. Try again in a moment."
CONNECTION_ERRORS = (OperationalError, InterfaceError, PoolTimeoutError)

logger = logging.getLogger(__name__)


@contextmanager
def database_guard(retry_button: bool = False):
    """Show a message if the database cannot be reached. Works with 'with' and as a decorator.

    Only connection problems are caught, so real bugs are not hidden. Parts that refresh by
    themselves try again on the next refresh; the rest of the page gets a Try again button.
    """
    try:
        yield
    except CONNECTION_ERRORS:
        logger.exception("The database could not be reached.")
        st.warning(DATABASE_MESSAGE, icon="⏳")
        if retry_button:
            st.button("Try again", key="retry_database")
