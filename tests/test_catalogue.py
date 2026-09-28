import httpx
import pytest

from recommendations.catalogue import PAGE_SIZE, fetch_movies

BASE = "http://catalogue.test"


def film(index: int) -> dict:
  """The shape webshow-core returns from /movies?view=full."""
  return {
    "id": f"01a0add2-0000-7000-8000-{index:012d}",
    "title": f"Film {index}",
    "releaseYear": 2000 + index,
    "overview": f"Plot {index}.",
    "genres": [{"id": "g", "name": "Action", "slug": "action"}],
    "cast": [{"id": "a", "name": f"Actor {index}", "profileUrl": None}],
  }


def pages(*bodies: dict) -> httpx.MockTransport:
  """Serves one body per request, in order, recording the queries it was asked."""
  seen: list[httpx.QueryParams] = []

  def handler(request: httpx.Request) -> httpx.Response:
    seen.append(request.url.params)
    return httpx.Response(200, json=bodies[len(seen) - 1])

  transport = httpx.MockTransport(handler)
  transport.seen = seen  # type: ignore[attr-defined]
  return transport


def test_collects_every_page():
  transport = pages(
    {"items": [film(1), film(2)], "hasMore": True},
    {"items": [film(3)], "hasMore": False},
  )

  movies = fetch_movies(BASE, transport=transport)

  assert [m.title for m in movies] == ["Film 1", "Film 2", "Film 3"]


def test_asks_for_full_objects_a_hundred_at_a_time():
  """The whole point of the endpoint: one pass, not a detail call per film."""
  transport = pages({"items": [film(1)], "hasMore": False})

  fetch_movies(BASE, transport=transport)

  assert transport.seen[0]["view"] == "full"
  assert transport.seen[0]["limit"] == str(PAGE_SIZE)


def test_pages_advance():
  transport = pages(
    {"items": [film(1)], "hasMore": True},
    {"items": [film(2)], "hasMore": False},
  )

  fetch_movies(BASE, transport=transport)

  assert [params["page"] for params in transport.seen] == ["1", "2"]


def test_maps_the_api_shape_not_the_database_shape():
  """The API promises `cast`; Prisma's relation is `actors`. Reading the wrong one is silent."""
  transport = pages({"items": [film(7)], "hasMore": False})

  movie = fetch_movies(BASE, transport=transport)[0]

  assert movie.cast == ["Actor 7"]
  assert movie.genres == ["Action"]
  assert movie.release_year == 2007


def test_an_empty_page_ends_the_loop_even_when_hasmore_lies():
  """Without this the job would never finish and never error."""
  transport = pages({"items": [], "hasMore": True})

  assert fetch_movies(BASE, transport=transport) == []


def test_a_failed_request_raises_rather_than_returning_a_partial_catalogue():
  transport = httpx.MockTransport(lambda request: httpx.Response(500, json={"error": "boom"}))

  with pytest.raises(httpx.HTTPStatusError):
    fetch_movies(BASE, transport=transport)
