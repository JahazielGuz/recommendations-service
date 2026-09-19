from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from pgvector.psycopg import register_vector

CONNECT_TIMEOUT_SECONDS = 5

@contextmanager
def connect(database_url: str, *, vectors: bool = True) -> Iterator[psycopg.Connection]:
  """A connection that commits on a clean exit and rolls back on an exception.

    `vectors` registers pgvector's type with psycopg, which needs the extension to already
    exist. The migration is the one caller that connects before that is true.
    """
    with psycopg.connect(database_url, connect_timeout=CONNECT_TIMEOUT_SECONDS) as connect:
      if vectors:
        register_vector(connection)

      yield connection
