from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from pgvector.psycopg import register_vector


@contextmanager
def connect(database_url: str, *, vectors: bool = True) -> Iterator[psycopg.Connection]:
    """A connection that commits on a clean exit and rolls back on an exception.

    `vectors` teaches psycopg to send and receive pgvector's type, which needs the extension to
    already exist. The migration is the one caller that connects before that is true.
    """
    with psycopg.connect(database_url) as connection:
        if vectors:
            register_vector(connection)

        yield connection
