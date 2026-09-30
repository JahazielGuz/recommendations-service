-- Genres are already inside the embedded document, but inside a vector they are only one signal
-- among many, blended with setting, tone and plot. Kept here as data as well, so a categorical
-- constraint can be enforced exactly rather than hoped for.
ALTER TABLE movie_embedding ADD COLUMN genres TEXT[] NOT NULL DEFAULT '{}';

-- GIN is the index for array overlap
CREATE INDEX movie_embedding_genres_idx ON movie_embedding USING gin (genres);
