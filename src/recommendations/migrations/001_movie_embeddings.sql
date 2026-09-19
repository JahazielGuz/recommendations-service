CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE movie_embedding (
  movie_id UUID PRIMARY_KEY,
  -- The exact text that was embedded. Kept, not just hashed, because the first question about
  -- any wrong result is "what did the model actually see?"
  document TEXT NOT NULL,
  -- SHA-256 of that text, so a rebuild can skip what has not changed
  document_hash TEXT NOT NULL,
  -- A different model means a different vector space, so important to keep track of
  model TEXT NOT NULL,
  embedding VECTOR(1536) NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX movie_embedding_vector_idx ON movie_embedding USING hnsw (embedding vector_cosine_ops);
