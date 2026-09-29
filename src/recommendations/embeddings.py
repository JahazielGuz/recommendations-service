from openai import OpenAI

from recommendations.config import require

# The endpoint takes an array. A hundred documents per call turns a thousand films into ten
# round trips while keeping each request small enough to be worth retrying.
BATCH = 100

MODEL = "text-embedding-3-small"
DIMENSIONS = 1536


def build_client() -> OpenAI:
    """The official client, which already retries connection errors and 429s with backoff."""
    return OpenAI(api_key=require("OPENAI_API_KEY"), timeout=60.0, max_retries=3)


def embed(client: OpenAI, documents: list[str]) -> list[list[float]]:
    """One vector per document, in the order the documents were given."""
    vectors: list[list[float]] = []

    for start in range(0, len(documents), BATCH):
        batch = documents[start : start + BATCH]

        response = client.embeddings.create(model=MODEL, dimensions=DIMENSIONS, input=batch)

        vectors.extend(
            item.embedding for item in sorted(response.data, key=lambda item: item.index)
        )
    return vectors
