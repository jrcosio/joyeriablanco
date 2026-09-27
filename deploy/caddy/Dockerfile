# syntax=docker/dockerfile:1.7
# Caddy con la SPA compilada (research R-15). Contexto de construcción: raíz del repositorio.

FROM node:26-trixie-slim AS web
WORKDIR /web
COPY joyeriablanco_web/package.json joyeriablanco_web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY joyeriablanco_web/ ./
RUN npm run build

FROM caddy:2.11-alpine
COPY deploy/caddy/Caddyfile /etc/caddy/Caddyfile
COPY deploy/caddy/tls-acme.caddy deploy/caddy/tls-internal.caddy /etc/caddy/
COPY --from=web /web/dist /srv
