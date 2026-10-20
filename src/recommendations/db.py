from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from pgvector.psycopg import register_vector
from psycopg_pool import NullConnectionPool

from recommendations.config import require

CONNECT_TIMEOUT_SECONDS = 5


@contextmanager
def connect(database_url: str, *, vectors: bool = True) -> Iterator[psycopg.Connection]:
    """A connection that commits on a clean exit and rolls back on an exception.
    `vectors` registers pgvector's type with psycopg, which needs the extension to already
    exist. The migration is the one caller that connects before that is true.
    """
    with psycopg.connect(database_url, connect_timeout=CONNECT_TIMEOUT_SECONDS) as connection:
        if vectors:
            register_vector(connection)

        yield connection


# A connection per request, closed as soon as the request is done, so nothing is left open to go
# stale. Fly suspends this machine about a minute after its last request, sooner than an idle
# connection was recycled, and a socket frozen through a suspend is dead when the machine wakes.
# Checking a pooled connection before use did not save it, because the check is a round trip on
# that same dead socket and blocked until the kernel gave up, minutes later. A fresh connection
# costs tens of milliseconds, against a two millisecond query, which this traffic can afford.
# The pool is built on first use rather than at import, so the CLI and the tests never open one
# they do not need.
_pool: NullConnectionPool | None = None


def _get_pool() -> NullConnectionPool:
    global _pool

    if _pool is None:
        _pool = NullConnectionPool(
            require("DATABASE_URL"),
            # Still a ceiling on how many connections are open at once
            max_size=10,
            # Fail fast rather than hanging: a caller waiting on a wedged pool is worse than a
            # caller told quickly that there is no answer
            timeout=10,
            # Every request now opens a connection, so one to a database that does not answer
            # gives up after a few seconds rather than hanging
            kwargs={"connect_timeout": CONNECT_TIMEOUT_SECONDS},
            open=True,
        )

    return _pool


@contextmanager
def pooled() -> Iterator[psycopg.Connection]:
    """A pooled connection with pgvector's type registered, returned to the pool on exit."""
    with _get_pool().connection() as connection:
        register_vector(connection)

        yield connection
