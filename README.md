# recs-service

Similar titles for [webshow](https://github.com/JahazielGuz/webshow-core): every movie in the
catalogue as a vector, stored in Postgres with **pgvector**.

## What it owns

Derived data, and nothing else. The service reads the catalogue over `webshow-core`'s public
API and never opens its database. Everything here is a function of the catalogue and the
embedding model, so this database can be dropped and rebuilt at any time; losing it costs one
rebuild, while losing the catalogue costs the catalogue.

| | |
| --- | --- |
| Language | Python 3.12, managed with `uv` |
| Store | its own Postgres on port 5433, from the `docker-compose.yml` in this repo |
| Embeddings | OpenAI, through the official client with a configurable base URL |

## Running it

```bash
cp .env.example .env          # then put a real OPENAI_API_KEY in it
docker compose up -d
uv sync
uv run recs migrate           # extension, table, HNSW index
uv run recs rebuild           # embed the catalogue
```

`rebuild` is safe to run as often as you like. Each movie is turned into a short document and
hashed; a movie is re-embedded only when that text changes, or when the embedding model does.
Running it twice in a row embeds nothing the second time.

## The document

The model only ever sees this text, so anything missing from it cannot influence the results.

```
Spider-Man: Brand New Day (2026)
Genres: Action, Adventure, Science Fiction
Starring: Tom Holland, Zendaya, Jacob Batalon, Marisa Tomei, Jon Bernthal
Fighting crime full-time as Spider-Man in a world that doesn't remember him...
```

Embedding the whole catalogue is roughly 105,000 tokens, which costs well under a cent with
`text-embedding-3-small` and takes about ten requests.

## Configuration

Every variable is listed in `.env.example`. Two are worth calling out: `OPENAI_BASE_URL` points
the client at any OpenAI-compatible endpoint, which is how the planned llm-gateway will sit in
front of this without a code change, and `EMBEDDING_MODEL` is part of what makes a row stale, so
changing it re-embeds the catalogue on the next rebuild.
