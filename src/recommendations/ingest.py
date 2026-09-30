from dataclasses import dataclass

from recommendations.catalogue import fetch_movies
from recommendations.config import require
from recommendations.db import connect
from recommendations.documents import build_document, document_hash
from recommendations.embeddings import MODEL, build_client, embed

UPSERT = """
  INSERT INTO movie_embedding
    (movie_id, document, document_hash, model, embedding, genres, updated_at)
  VALUES (%s, %s, %s, %s, %s, %s, now())
  ON CONFLICT (movie_id) DO UPDATE SET
    document = EXCLUDED.document,
    document_hash = EXCLUDED.document_hash,
    model = EXCLUDED.model,
    embedding = EXCLUDED.embedding,
    genres = EXCLUDED.genres,
    updated_at = now()
"""


@dataclass(frozen=True)
class RebuildReport:
    catalogue: int
    embedded: int
    unchanged: int
    removed: int


def rebuild() -> RebuildReport:
    """Bring every stored vector up to date with the catalogue, embedding only what changed."""
    movies = fetch_movies(require("CORE_BASE_URL"))

    # An empty catalogue is a broken read, not an instruction to delete everything
    if not movies:
        raise RuntimeError("The catalogue returned no movies; refusing to rebuild")

    documents = {movie.id: build_document(movie) for movie in movies}
    genres = {movie.id: movie.genres for movie in movies}

    with connect(require("DATABASE_URL")) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT movie_id, document_hash, model FROM movie_embedding")
            stored = {str(row[0]): (row[1], row[2]) for row in cursor.fetchall()}

        stale = [
            movie_id
            for movie_id, document in documents.items()
            if stored.get(movie_id) != (document_hash(document), MODEL)
        ]

        if stale:
            client = build_client()
            vectors = embed(client, [documents[movie_id] for movie_id in stale])

            rows = [
                (
                    movie_id,
                    documents[movie_id],
                    document_hash(documents[movie_id]),
                    MODEL,
                    vector,
                    genres[movie_id],
                )
                for movie_id, vector in zip(stale, vectors, strict=True)
            ]

            with connection.cursor() as cursor:
                cursor.executemany(UPSERT, rows)

        # Genres are refreshed for every film, not only the stale ones. They are part of the
        # document, so a change to them re-embeds anyway; this pass exists so that a column
        # added after the vectors were written fills without paying to re-embed a thousand
        # films that have not otherwise changed.
        with connection.cursor() as cursor:
            cursor.executemany(
                "UPDATE movie_embedding SET genres = %s WHERE movie_id = %s::uuid",
                [(names, movie_id) for movie_id, names in genres.items()],
            )

        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM movie_embedding WHERE movie_id <> ALL(%s::uuid[])", (list(documents),)
            )
            removed = cursor.rowcount

    return RebuildReport(
        catalogue=len(movies),
        embedded=len(stale),
        unchanged=len(documents) - len(stale),
        removed=removed,
    )
