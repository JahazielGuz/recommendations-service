from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from pgvector.psycopg import register_vector
from psycopg_pool import ConnectionPool

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


# Opening a connection costs more than the query it would carry: a nearest-neighbour lookup is
# about two milliseconds, a fresh Postgres connection tens. The pool is built on first use rather
# than at import, so the CLI and the tests never open one they do not need.
_pool: ConnectionPool | None = None


def _get_pool() -> ConnectionPool:
    global _pool

    if _pool is None:
        _pool = ConnectionPool(require("DATABASE_URL"), min_size=1, max_size=10, open=True)

    return _pool


@contextmanager
def pooled() -> Iterator[psycopg.Connection]:
    """A pooled connection with pgvector's type registered, returned to the pool on exit."""
    with _get_pool().connection() as connection:
        register_vector(connection)

        yield connection
