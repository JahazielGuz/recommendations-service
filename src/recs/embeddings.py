from openai import OpenAI

from recs.config import Settings

# The endpoint takes an array. A hundred documents per call turns a thousand movies into ten
# round trips while keeping each request small enough to be worth retrying.
BATCH = 100


def build_client(settings: Settings) -> OpenAI:
    """The official client, which already retries on connection errors and 429s with backoff."""
    return OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)


def embed(client: OpenAI, settings: Settings, documents: list[str]) -> list[list[float]]:
    """One vector per document, in the order the documents were given."""
    vectors: list[list[float]] = []

    for start in range(0, len(documents), BATCH):
        batch = documents[start : start + BATCH]

        response = client.embeddings.create(
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
            input=batch,
        )

        # The API returns the batch in order and labels each item with its index. Sorting on
        # that index means the pairing with the documents cannot silently drift.
        vectors.extend(item.embedding for item in sorted(response.data, key=lambda item: item.index))

    return vectors
