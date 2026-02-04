FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE="copy" \
    UV_NO_DEV=1 \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

COPY src .


FROM python:3.14-slim-trixie AS runner

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UVICORN_HOST="0.0.0.0" \
    FORWARDED_ALLOW_IPS="*" \
    DB_URL="postgres://postgres:rinha@db:5432/postgres"

WORKDIR /app

RUN groupadd --system --gid 999 rinha \
    && useradd --system --create-home --gid 999 --uid 999 rinha

COPY --from=builder --chown=rinha:rinha /app /app

USER rinha

CMD ["uvicorn", "--no-access-log", "--http=httptools", "--loop=uvloop" "rinha24.main:app"]
