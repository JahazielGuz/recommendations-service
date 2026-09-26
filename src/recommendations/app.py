import time

from fastapi import FastAPI

STARTED_AT = time.monotonic()

def create_app() -> FastAPI:
  """Builds the application, A function, so a test can make a fresh one per case."""
  app = FastAPI(title="recommendations-service", version="0.1.0")

  @app.get("/health")
  def health() -> dict[str, object]:
    """Liveness only: it must never touch the database or the catalogue."""
    return { "status": "ok", "uptime": time.monotonic() - STARTED_AT}
  
  return app

app = create_app()
