from dataclasses import dataclass

from recs.catalogue import fetch_movies
from recs.config import Settings
from recs.db import connect
from recs.documents import build_document, document_hash
from recs.embeddings import build_client, embed

UPSERT = """
    INSERT INTO movie_embedding (movie_id, document_hash, model, embedding, updated_at)
    VALUES (%s, %s, %s, %s, now())
    ON CONFLICT (movie_id) DO UPDATE SET
        document_hash = EXCLUDED.document_hash,
        model = EXCLUDED.model,
        embedding = EXCLUDED.embedding,
        updated_at = now()
"""


@dataclass(frozen=True)
class RebuildReport:
    catalogue: int
    embedded: int
    unchanged: int
    removed: int


def rebuild(settings: Settings) -> RebuildReport:
    """Bring every stored vector up to date with the catalogue, embedding only what changed."""
    movies = fetch_movies(settings.core_base_url)

    # An empty catalogue is a broken read, not an instruction to delete everything
    if not movies:
        raise RuntimeError("The catalogue returned no movies; refusing to rebuild")

    documents = {movie.id: build_document(movie) for movie in movies}

    with connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT movie_id, document_hash, model FROM movie_embedding")
            stored = {str(row[0]): (row[1], row[2]) for row in cursor.fetchall()}

        # A row is stale when its text changed, and also when a different model produced it:
        # vectors are only comparable with others from the same model.
        stale = [
            movie_id
            for movie_id, document in documents.items()
            if stored.get(movie_id) != (document_hash(document), settings.embedding_model)
        ]

        if stale:
            client = build_client(settings)
            vectors = embed(client, settings, [documents[movie_id] for movie_id in stale])

            rows = [
                (movie_id, document_hash(documents[movie_id]), settings.embedding_model, vector)
                for movie_id, vector in zip(stale, vectors, strict=True)
            ]

            with connection.cursor() as cursor:
                cursor.executemany(UPSERT, rows)

        # Films that have left the catalogue leave their vectors behind, and a vector with no
        # movie is a result nobody can render
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM movie_embedding WHERE movie_id <> ALL(%s::uuid[])",
                (list(documents),),
            )
            removed = cursor.rowcount

    return RebuildReport(
        catalogue=len(movies),
        embedded=len(stale),
        unchanged=len(documents) - len(stale),
        removed=removed,
    )
