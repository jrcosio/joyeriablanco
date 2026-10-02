import type { FiltrosFacturas } from '../api/queries/facturas'

/**
 * URL de los PDF (003, research R-8): la web no los descarga; abre la ruta de la API en una
 * pestaña nueva con un enlace (contracts/ui-rutas.md). La cookie de sesión va en la navegación.
 */
const BASE = '/api/v1/facturas'

function conParametros(ruta: string, parametros: URLSearchParams): string {
  const consulta = parametros.toString()
  return consulta ? `${ruta}?${consulta}` : ruta
}

export interface OpcionesImpresion {
  iban?: boolean
  duplicado?: boolean
}

/** «Imprimir» de una factura: `iban` y `duplicado` solo si están marcadas (FR-010, FR-033). */
export function urlPdfFactura(
  id: string,
  { iban = false, duplicado = false }: OpcionesImpresion = {},
): string {
  const parametros = new URLSearchParams()
  if (iban) parametros.set('iban', 'true')
  if (duplicado) parametros.set('duplicado', 'true')
  return conParametros(`${BASE}/${encodeURIComponent(id)}/pdf`, parametros)
}

/**
 * «Imprimir listado»: los filtros de la pantalla tal como están en la URL, sin la página y sin los
 * valores por defecto, que el servidor aplica igual que en el listado (FR-018).
 */
export function urlPdfListado(filtros: FiltrosFacturas): string {
  const parametros = new URLSearchParams()
  if (filtros.q) parametros.set('q', filtros.q)
  if (filtros.anio !== undefined) parametros.set('anio', String(filtros.anio))
  if (filtros.mes !== undefined) parametros.set('mes', String(filtros.mes))
  if (filtros.orden !== 'recientes') parametros.set('orden', filtros.orden)
  return conParametros(`${BASE}/listado/pdf`, parametros)
}

/** Máximo de filas del listado impreso (FR-018; Clarifications). El servidor lo vuelve a exigir. */
export const LIMITE_LISTADO_IMPRESO = 5000

/** Tiempo durante el que «Imprimir» ignora otro clic (FR-023). */
export const ESPERA_IMPRESION_MS = 2000
