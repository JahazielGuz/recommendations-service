import random
from dataclasses import dataclass

from psycopg import Connection

# How many nearest films to consider before choosing. Twenty is wide enough that two rows built
# from the same film differ, and narrow enough that the twentieth is still a defensible answer.
DEFAULT_POOL = 20
DEFAULT_LIMIT = 12

# Cosine distance, ordered so the HNSW index is used. `1 - distance` is the similarity a human
# reads the right way round. The subject is excluded by id, not by score: a remake of the same
# film is a legitimate neighbour, but the film itself never is.
NEAREST = """
    SELECT m.movie_id::text, 1 - (m.embedding <=> subject.embedding) AS score
    FROM movie_embedding AS m,
         (SELECT embedding FROM movie_embedding WHERE movie_id = %s::uuid) AS subject
    WHERE m.movie_id <> %s::uuid
    ORDER BY m.embedding <=> subject.embedding
    LIMIT %s
"""


@dataclass(frozen=True)
class Neighbour:
    movie_id: str
    score: float


def nearest(connection: Connection, movie_id: str, pool: int) -> list[Neighbour]:
    """The `pool` closest films to this one, nearest first. Empty when the film has no vector."""
    with connection.cursor() as cursor:
        cursor.execute(NEAREST, (movie_id, movie_id, pool))
        rows = cursor.fetchall()

    return [Neighbour(movie_id=row[0], score=row[1]) for row in rows]


def choose(candidates: list[Neighbour], limit: int, shuffle: bool) -> list[Neighbour]:
    """Pick what to show from the pool.

    Shuffling is the default because the same film's neighbours appear in more than one place on
    a page, and two identical rows read as a bug. Drawing from a pool rather than reordering the
    whole catalogue means the variety costs relevance only down to the pool's worst member.

    With `shuffle` off the top `limit` come back in rank order, which is what an evaluation
    needs: a metric cannot measure a list that changes between runs.
    """
    if not shuffle:
        return candidates[:limit]

    return random.sample(candidates, min(limit, len(candidates)))
