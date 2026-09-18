from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import httpx

# The catalogue's own page cap
PAGE_SIZE = 50
# Detail calls run in parallel because each is a round trip that spends its time waiting. Ten
# is polite to a service that is also serving a website.
WORKERS = 10
TIMEOUT = httpx.Timeout(30.0)


@dataclass(frozen=True)
class Movie:
    id: str
    title: str
    release_year: int
    genres: list[str]
    cast: list[str]
    overview: str


def _movie_ids(client: httpx.Client, base_url: str) -> list[str]:
    """Every id in the catalogue, a page at a time until the API says there are no more."""
    ids: list[str] = []
    page = 1

    while True:
        response = client.get(f"{base_url}/movies", params={"page": page, "limit": PAGE_SIZE})
        response.raise_for_status()
        body = response.json()

        ids.extend(item["id"] for item in body["items"])

        if not body["hasMore"]:
            return ids

        page += 1


def _movie(client: httpx.Client, base_url: str, movie_id: str) -> Movie:
    """One movie with the fields a document is built from, which the list endpoint does not carry."""
    response = client.get(f"{base_url}/movies/{movie_id}")
    response.raise_for_status()
    body = response.json()

    return Movie(
        id=body["id"],
        title=body["title"],
        release_year=body["releaseYear"],
        genres=[genre["name"] for genre in body["genres"]],
        cast=[actor["name"] for actor in body["cast"]],
        overview=body["overview"],
    )


def fetch_movies(base_url: str) -> list[Movie]:
    """The whole catalogue, read over the public API.

    This service never opens webshow-core's database. Everything it stores is derived from what
    any other client could fetch, which is what makes a rebuild from nothing possible.
    """
    with httpx.Client(timeout=TIMEOUT) as client:
        ids = _movie_ids(client, base_url)

        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            movies = list(pool.map(lambda movie_id: _movie(client, base_url, movie_id), ids))

    return movies
