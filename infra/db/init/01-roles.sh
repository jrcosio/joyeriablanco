#!/usr/bin/env bash
# Inicialización de PostgreSQL (solo se ejecuta al crear el volumen de datos).
#
# Crea los roles de la aplicación (research R-11) y las bases de datos:
#   - jb_owner: dueño del esquema; ejecuta las migraciones (DDL).
#   - jb_app:   rol de la API; solo DML, sin capacidad de alterar la estructura.
# Bases: joyeriablanco (desarrollo/producción), joyeriablanco_test (pytest) y
# joyeriablanco_e2e (Playwright).
set -euo pipefail

: "${DB_OWNER_PASSWORD:?Falta DB_OWNER_PASSWORD}"
: "${DB_APP_PASSWORD:?Falta DB_APP_PASSWORD}"
BASES="${JB_BASES:-joyeriablanco joyeriablanco_test joyeriablanco_e2e}"

psql -v ON_ERROR_STOP=1 \
  -v owner_pwd="$DB_OWNER_PASSWORD" \
  -v app_pwd="$DB_APP_PASSWORD" \
  --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-'EOSQL'
	CREATE ROLE jb_owner LOGIN PASSWORD :'owner_pwd';
	CREATE ROLE jb_app LOGIN PASSWORD :'app_pwd' NOCREATEDB NOCREATEROLE;
EOSQL

for base in $BASES; do
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    -c "CREATE DATABASE ${base} OWNER jb_owner ENCODING 'UTF8' TEMPLATE template0"

  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$base" <<-EOSQL
	REVOKE ALL ON DATABASE ${base} FROM PUBLIC;
	GRANT CONNECT, TEMPORARY ON DATABASE ${base} TO jb_app;
	ALTER SCHEMA public OWNER TO jb_owner;
	REVOKE ALL ON SCHEMA public FROM PUBLIC;
	GRANT USAGE ON SCHEMA public TO jb_app;
	-- Extensiones de confianza; se crean aquí como superusuario por robustez.
	CREATE EXTENSION IF NOT EXISTS unaccent SCHEMA public;
	CREATE EXTENSION IF NOT EXISTS pg_trgm SCHEMA public;
EOSQL
done

echo "Roles jb_owner/jb_app y bases [${BASES}] creados."
