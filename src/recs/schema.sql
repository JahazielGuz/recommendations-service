-- Everything here is derived from the catalogue and can be rebuilt from it, so the schema is
-- applied idempotently rather than through a migration history. Losing this database costs one
-- rebuild; losing webshow-core's costs the catalogue.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS movie_embedding (
    movie_id UUID PRIMARY KEY,
    -- SHA-256 of the exact text that was embedded, so a rebuild can skip what has not changed
    document_hash TEXT NOT NULL,
    -- The model that produced the vector. A different model means a different vector space,
    -- so changing it makes every row stale even when the document is identical.
    model TEXT NOT NULL,
    embedding VECTOR(1536) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- HNSW rather than IVFFlat: no training step, and it keeps its recall as rows are added one at
-- a time. Cosine distance, because that is what the embeddings are normalised for.
CREATE INDEX IF NOT EXISTS movie_embedding_vector_idx
    ON movie_embedding USING hnsw (embedding vector_cosine_ops);
