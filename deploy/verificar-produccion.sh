#!/usr/bin/env bash
# Verifica el despliegue de producción (FR-046 a FR-049, SC-011 en su parte local).
# Uso: deploy/verificar-produccion.sh [dominio]   (por defecto, localhost con la CA interna)
set -uo pipefail

DOMINIO="${1:-localhost}"
BASE="https://${DOMINIO}"
CURL=(curl -sS --max-time 10)
if [[ "$DOMINIO" == "localhost" ]]; then
  CURL+=(-k) # certificado de la CA interna de Caddy
fi
cd "$(dirname "$0")/.."

fallos=0
comprobar() {
  if eval "$2"; then
    echo "✔ $1"
  else
    echo "✘ $1"
    fallos=$((fallos + 1))
  fi
}

redireccion=$(curl -s -o /dev/null -w "%{http_code} %{redirect_url}" "http://${DOMINIO}/")
comprobar "HTTP redirige a HTTPS (308)" '[[ "$redireccion" == 308\ https://* ]]'

cabeceras=$("${CURL[@]}" -D - -o /dev/null "$BASE/")
for cabecera in strict-transport-security content-security-policy x-content-type-options \
  referrer-policy permissions-policy; do
  comprobar "Cabecera ${cabecera}" 'grep -qi "^${cabecera}:" <<<"$cabeceras"'
done
comprobar "CSP con frame-ancestors 'none' y sin unsafe-inline" \
  'grep -qi "frame-ancestors '"'"'none'"'"'" <<<"$cabeceras" && ! grep -qi "unsafe-inline" <<<"$cabeceras"'
comprobar "Sin cabecera Server" '! grep -qi "^server:" <<<"$cabeceras"'

salud=$("${CURL[@]}" "$BASE/api/salud")
comprobar "/api/salud responde ok" '[[ "$salud" == *"\"ok\""* ]]'
sesion=$("${CURL[@]}" -o /dev/null -w "%{http_code}" "$BASE/api/v1/sesion")
comprobar "/api/v1/sesion sin cookie responde 401" '[[ "$sesion" == 401 ]]'
docs=$("${CURL[@]}" -o /dev/null -w "%{http_code}" "$BASE/api/docs")
comprobar "Documentación interactiva de la API desactivada" '[[ "$docs" == 404 ]]'
# PDF (003, research R-8): sin sesión responde 401 con la CSP propia de la API, no con la global.
pdf=$("${CURL[@]}" -D - -o /dev/null "$BASE/api/v1/facturas/listado/pdf")
comprobar "PDF sin sesión responde 401" 'grep -q "^HTTP/[0-9.]* 401" <<<"$pdf"'
comprobar "PDF con la CSP de la API (object-src 'self')" \
  'grep -qi "^content-security-policy:.*object-src '"'"'self'"'"'" <<<"$pdf"'
comprobar "PDF sin la CSP global de la SPA" \
  '! grep -qi "^content-security-policy:.*script-src '"'"'self'"'"'" <<<"$pdf"'
# Presupuestos (005): sus PDF tienen la misma excepción en el Caddyfile.
pdf_pre=$("${CURL[@]}" -D - -o /dev/null "$BASE/api/v1/presupuestos/listado/pdf")
comprobar "PDF de presupuestos sin sesión responde 401" 'grep -q "^HTTP/[0-9.]* 401" <<<"$pdf_pre"'
comprobar "PDF de presupuestos con la CSP de la API (object-src 'self')" \
  'grep -qi "^content-security-policy:.*object-src '"'"'self'"'"'" <<<"$pdf_pre"'
comprobar "PDF de presupuestos sin la CSP global de la SPA" \
  '! grep -qi "^content-security-policy:.*script-src '"'"'self'"'"'" <<<"$pdf_pre"'
comprobar "La SPA mantiene object-src 'none'" \
  'grep -qi "^content-security-policy:.*object-src '"'"'none'"'"'" <<<"$cabeceras"'
spa=$("${CURL[@]}" -o /dev/null -w "%{http_code}" "$BASE/clientes")
comprobar "Las rutas de la SPA se sirven (fallback a index.html)" '[[ "$spa" == 200 ]]'

# Declaración responsable (004, US5): su PDF tiene la misma excepción de CSP en el Caddyfile.
pdf_decl=$("${CURL[@]}" -D - -o /dev/null "$BASE/api/v1/sistema/declaracion-responsable/pdf")
comprobar "PDF de la declaración sin sesión responde 401" 'grep -q "^HTTP/[0-9.]* 401" <<<"$pdf_decl"'
comprobar "PDF de la declaración con la CSP de la API (object-src 'self')" \
  'grep -qi "^content-security-policy:.*object-src '"'"'self'"'"'" <<<"$pdf_decl"'

# Certificado de firma (004, research R-6): instalado y utilizable en la API. Código 3: caduca en
# 30 días o menos (contracts/cli.md de 004).
docker compose -f docker-compose.prod.yml exec -T api joyeria estado-certificado
estado_certificado=$?
comprobar "Certificado de firma utilizable (joyeria estado-certificado)" \
  '[[ "$estado_certificado" == 0 || "$estado_certificado" == 3 ]]'
if [[ "$estado_certificado" == 3 ]]; then echo "  Aviso: el certificado caduca en 30 días o menos."; fi

contenedor_db=$(docker compose -f docker-compose.prod.yml ps -q db)
puertos=$(docker inspect --format '{{json .NetworkSettings.Ports}}' "$contenedor_db" 2>/dev/null)
# Publicado sería p. ej. {"5432/tcp":[{"HostIp":"0.0.0.0","HostPort":"5432"}]}; sin publicar: null.
comprobar "La base de datos no publica puertos" '[[ -n "$contenedor_db" && "$puertos" != *HostPort* ]]'

echo
if ((fallos == 0)); then echo "Todas las comprobaciones han pasado."; else echo "Fallos: ${fallos}"; fi
exit "$fallos"
