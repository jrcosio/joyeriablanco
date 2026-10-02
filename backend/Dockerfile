# syntax=docker/dockerfile:1.7
# API de Joyería Blanco — imagen multietapa (research R-1, R-15)
#   target dev:  recarga en caliente, dependencias de desarrollo, código montado por volumen
#   target prod: sin dependencias de desarrollo, usuario sin privilegios, healthcheck

FROM ghcr.io/astral-sh/uv:0.12 AS uv

# ---------------------------------------------------------------------------- base
FROM python:3.13.15-slim-trixie AS base
COPY --from=uv /uv /uvx /bin/
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    TZ=Europe/Madrid
# WeasyPrint (PDF de 003, research R-4): Pango y HarfBuzz; DejaVu como último recurso de glifos.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --home-dir /app --no-create-home app
WORKDIR /app

# ----------------------------------------------------------------------------- dev
FROM base AS dev
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project
COPY . .
RUN uv sync --frozen && chown -R app:app /opt/venv
# Caché de fontconfig fuera de /app, que es el código montado (research R-4). Se fija después de
# `uv sync` para que la construcción, como root, no cree el directorio antes que `app`.
ENV XDG_CACHE_HOME=/tmp/cache
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--reload", "--no-server-header"]

# ---------------------------------------------------------------------- prod-build
FROM base AS prod-build
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
RUN uv sync --frozen --no-dev --no-editable

# ---------------------------------------------------------------------------- prod
FROM python:3.13.15-slim-trixie AS prod
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/opt/venv/bin:$PATH \
    TZ=Europe/Madrid \
    ENTORNO=produccion \
    XDG_CACHE_HOME=/tmp/cache
# XDG_CACHE_HOME: la caché de fontconfig va al tmpfs /tmp, porque el contenedor es read_only.
# Mismas librerías del sistema que `base` para WeasyPrint (research R-4): prod parte de cero.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --home-dir /app --no-create-home app
WORKDIR /app
COPY --from=prod-build /opt/venv /opt/venv
COPY --from=prod-build /app/alembic ./alembic
COPY --from=prod-build /app/alembic.ini ./
USER app
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/salud', timeout=2)"]
# FORWARDED_ALLOW_IPS lo fija docker-compose.prod.yml (solo Caddy llega a la API)
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers", "--no-server-header"]
