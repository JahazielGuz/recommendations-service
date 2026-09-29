# syntax=docker/dockerfile:1

FROM python:3.12-slim AS build

# uv is copied from its own published image rather than installed with pip: one pinned binary,
# no Python packaging bootstrap, and nothing left behind in the layer.
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

WORKDIR /app
# Bytecode is compiled at build time so the first request does not pay for it, and packages are
# copied rather than hard-linked because the cache and the target are different layers here.
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Dependencies first, without the project. This layer is rebuilt only when the lock file
# changes, so editing a source file does not reinstall the world.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --no-dev

COPY src ./src
RUN uv sync --locked --no-dev

FROM python:3.12-slim AS runtime

WORKDIR /app
# The virtual environment is self-contained, so the runtime stage needs no uv and no build tools
COPY --from=build /app/.venv /app/.venv
COPY --from=build /app/src /app/src
ENV PATH="/app/.venv/bin:$PATH"

# Run as an ordinary user rather than an administrator. Everything above ran as root, so the
# code stays root-owned and read-only to this process: if it is ever tricked into running
# someone else's code, that code cannot rewrite the app and a restart clears it.
RUN useradd --create-home --uid 1000 app
USER app

EXPOSE 8000
CMD ["uvicorn", "recommendations.app:app", "--host", "0.0.0.0", "--port", "8000"]
