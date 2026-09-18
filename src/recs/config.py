import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Read .env once, if there is one. In production the platform supplies the environment and
# there is no file, which load_dotenv treats as nothing to do.
load_dotenv()


def required(name: str) -> str:
    """The value of an environment variable, or a written error naming the one that is missing."""
    value = os.environ.get(name)

    if not value:
        raise RuntimeError(f"{name} is not set")

    return value


@dataclass(frozen=True)
class Settings:
    database_url: str
    core_base_url: str
    openai_api_key: str
    # None means the official API. Any OpenAI-compatible endpoint works, which is how the
    # llm-gateway will be slotted in front later without touching this code.
    openai_base_url: str | None
    embedding_model: str
    embedding_dimensions: int


def load_settings() -> Settings:
    """Everything the rebuild needs, read up front so a missing variable fails before any work."""
    return Settings(
        database_url=required("DATABASE_URL"),
        core_base_url=required("CORE_BASE_URL").rstrip("/"),
        openai_api_key=required("OPENAI_API_KEY"),
        openai_base_url=os.environ.get("OPENAI_BASE_URL"),
        embedding_model=os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small"),
        embedding_dimensions=int(os.environ.get("EMBEDDING_DIMENSIONS", "1536")),
    )
