# Backend — API de Joyería Blanco

API REST con FastAPI sobre PostgreSQL 18, gestionada con `uv`. La especificación de la feature en
curso está en [`specs/001-cimientos-clientes/`](../specs/001-cimientos-clientes/). La guía de puesta en
marcha está en [`quickstart.md`](../specs/001-cimientos-clientes/quickstart.md).

## Capas

```
app/api (routers) → app/services → app/repositories → app/models
app/domain: reglas puras, testables sin HTTP ni BD
app/schemas: esquemas Pydantic de entrada (*Entrada) y salida (*Salida)
```

## Comandos

```bash
uv sync                      # dependencias
uv run pytest                # tests (BD joyeriablanco_test del servicio db)
uv run ruff check . && uv run ruff format --check . && uv run mypy .
uv run alembic upgrade head  # migraciones (como jb_owner)
uv run joyeria --help        # CLI de operación
```
