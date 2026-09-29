# recommendations-service

Retrieval for [webshow](https://github.com/JahazielGuz/webshow-core): every film in the catalogue
as a vector, so the site can answer "what else is like this".

**Python 3.12 · FastAPI · Postgres + pgvector · OpenAI embeddings · uv**

## What it owns

Derived data, and nothing else. This service reads the catalogue over `webshow-core`'s public API
and never opens its database. Everything stored here is a function of the catalogue and the
embedding model, so this database can be dropped and rebuilt at any time: losing it costs one
rebuild, while losing the catalogue costs the catalogue.

That is also why it declares its own store. The `docker-compose.yml` in this repository runs
pgvector on port 5433, so the service starts from its own clone with nothing else present.

## Running it

```bash
cp .env.example .env      # then fill in OPENAI_API_KEY
docker compose up -d
uv sync
uv run recommendations migrate    # extension, table, HNSW index
uv run recommendations rebuild    # embed the catalogue
```

`rebuild` is safe to run as often as you like. It prints what it did:

```
catalogue 1000, embedded 1000, unchanged 0, removed 0
```

Run it again immediately and the second line reads `embedded 0, unchanged 1000`.

## The document

Each film is flattened into one block of text. The model only ever sees this string, so anything
left out of it cannot influence which films come back as similar. It is the highest-leverage
choice in the pipeline and deliberately lives in one readable function.

```
Spider-Man: Brand New Day (2026)
Genres: Action, Adventure, Science Fiction
Starring: Florence Pugh, Jacob Batalon, Jon Bernthal, Liza Colón-Zayas, Marisa Tomei
Fighting crime full-time as Spider-Man in a world that doesn't remember him...
```

Billing is capped at five names. Cast is a real similarity signal, but a long list of names drowns
out the plot. That number is a guess worth revisiting once there is an evaluation to revisit it
against, and the document hash is what makes trying another value cost one rebuild.

## Serving

```bash
uv run uvicorn recommendations.app:app --port 8100
```

| Endpoint | Answers |
| --- | --- |
| `GET /health` | Is the process alive? Touches nothing. |
| `GET /ready` | Can this instance serve? Counts the vectors, so a machine that cannot reach them is taken out of rotation rather than restarted. |
| `GET /similar/{movie_id}` | Films like this one, as ids and scores. |

`/similar` takes three parameters. `limit` is how many to return, `pool` is how many nearest
films to choose from, and `shuffle` decides whether to sample from that pool or return the top
`limit` in rank order.

Shuffling is on by default because the same film's neighbours appear in more than one place on a
page, and two identical rows read as a bug. Drawing from a pool of twenty rather than reordering
the whole catalogue means the variety costs relevance only down to the pool's worst member.

Turn it off for measurement: a metric cannot evaluate a list that changes between runs.

```
GET /similar/{id}?shuffle=false&limit=6

0.683  Spider-Man: No Way Home
0.644  Spider-Man: Across the Spider-Verse
0.634  Spider-Man: Homecoming
0.627  Spider-Man: Far From Home
0.617  Avengers: Doomsday
0.587  The Amazing Spider-Man 2
```

The service returns ids, never titles or posters. It does not own those, and the caller joins
them back to the catalogue.

## What a rebuild costs

| | |
| --- | --- |
| Requests to read the catalogue | 10 |
| Time to read it | under a second |
| Tokens to embed 1,000 films | about 100,000 |
| Cost with `text-embedding-3-small` | under one cent |

The catalogue is read a hundred films at a time through `/movies?view=full`, an endpoint added for
this caller. Before it, ingestion meant twenty calls to page the ids and then a thousand calls to
fetch each film for its overview, genres and cast.

## How it decides what to re-embed

Each row stores a SHA-256 of the exact text that was embedded, and the name of the model that
produced the vector. A film is re-embedded when either changes.

The model is part of that comparison because vectors are only comparable within one model, so
switching models invalidates every row without a single document changing. The width is part of
the column type, `VECTOR(1536)`, so a model of a different size is a migration rather than a
setting, which is why both live as constants in `embeddings.py`.

Films that have left the catalogue lose their vectors on the next rebuild. A vector with no film
behind it is a recommendation the frontend has nothing to render.

## Migrations

Numbered SQL files under `src/recommendations/migrations`, applied oldest first and recorded by
name in a `schema_migration` table. The whole run happens in one transaction, so a migration that
fails halfway cannot leave a recorded version that did not apply.

There are no Alembic models here, because autogenerate is what earns Alembic its ceremony and
there is nothing to generate from. And there will never be a **data** migration: everything in
this database is derived, so anything that would need a backfill is a rebuild instead.

## Tests

```bash
uv run pytest
```

They cover the two pieces that fail silently rather than loudly: the document builder, where a
truncated overview or an uncapped cast list would change every result without erroring, and the
catalogue client, where reading the wrong field or trusting a paging flag would produce a store
that looks healthy and is wrong. `httpx.MockTransport` drives the paging loop without a server,
which is the only way to reach the empty-page and non-200 branches.

## Configuration

Every variable is listed in `.env.example`. `CORE_BASE_URL` points at the catalogue, local or
deployed. `OPENAI_API_KEY` is the only secret.
