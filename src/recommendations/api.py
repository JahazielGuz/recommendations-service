from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from recommendations.db import pooled
from recommendations.similar import DEFAULT_LIMIT, DEFAULT_POOL, choose, nearest

router = APIRouter()


@router.get("/similar/{movie_id}")
def similar(
    movie_id: UUID,
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=50),
    pool: int = Query(DEFAULT_POOL, ge=1, le=100),
    shuffle: bool = True,
) -> dict[str, object]:
    """Films like this one, as ids and scores. The caller turns them back into movies."""
    with pooled() as connection:
        candidates = nearest(connection, str(movie_id), max(pool, limit))

    # No vector means either an unknown film or one the rebuild has not reached yet. Both are
    # "nothing to say about this id" rather than a server fault.
    if not candidates:
        raise HTTPException(status_code=404, detail="No embedding for that movie")

    chosen = choose(candidates, limit, shuffle)

    return {"items": [{"movieId": n.movie_id, "score": n.score} for n in chosen]}
