import time

from fastapi import FastAPI

from recommendations.api import router
from recommendations.db import pooled

STARTED_AT = time.monotonic()


def create_app() -> FastAPI:
    """Builds the application, A function, so a test can make a fresh one per case."""
    app = FastAPI(title="recommendations-service", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, object]:
        """Liveness only: it must never touch the database or the catalogue."""
        return {"status": "ok", "uptime": time.monotonic() - STARTED_AT}

    @app.get("/ready")
    def ready() -> dict[str, object]:
        """Readiness, which is a different question: can this instance actually serve?

        Liveness above answers "is the process alive" and must never touch the database, or a
        database blip becomes a restart loop. This one deliberately does touch it, because an
        instance that cannot reach its vectors should be taken out of rotation rather than
        restarted.
        """
        with pooled() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM movie_embedding")
                stored = cursor.fetchone()[0]

        return {"status": "ready", "vectors": stored}

    app.include_router(router)

    return app


app = create_app()
