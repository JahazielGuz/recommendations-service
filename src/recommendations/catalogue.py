from dataclasses import dataclass

import httpx 

PAGE_SIZE = 100
TIMEOUT = httpx.Timeout(30.0)

@dataclass(frozen=True)
class Movie:
  id: str
  title: str
  release_year: int
  genres: list[str]
  cast: list[str]
  overview: str

def _to_movie(body: dict) -> Movie:
  """Only the fields a document is built from. Posters and runtimes are not similarity signals."""
  return Movie(
    id=body["id"],
    title=body["title"],
    release_year=body["releaseYear"],
    genres=[genre["name"] for genre in body["genres"]],
    cast=[actor["name"] for actor in body["cast"]],
    overview=body["overview"]
  )

def fetch_movies(base_url: str) -> list[Movie]:
  """The whole catalogue, read over the public API.
  This service never opens webshow-core's database. Everything it stores is derived from what
  any other client could fetch, which is what makes a rebuild from nothing possible.
  """
  movies: list[Movie] = []
  page = 1

  with httpx.Client(timeout=TIMEOUT) as client:
    while True:
      response = client.get(
        f"{base_url}/movies",
        params={"page": page, "limit": PAGE_SIZE, "view": "full"}
      )
      response.raise_for_status()
      body = response.json()
      items = body["items"]

      # A page with nothing in it ends the loop regardless of what hasMore claims, so a server
      # bug cannot turn this into a job that never finishes and never errors
      if not items:
        return movies

      movies.extend(_to_movie(item) for item in items)

      if not body["hasMore"]:
        return movies
      
      page += 1
