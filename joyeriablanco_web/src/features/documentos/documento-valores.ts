/**
 * Lo común de los formularios de factura y de presupuesto (005, research R-13): las líneas, su
 * validación de forma, el cuerpo para la API y su previsualización.
 *
 * Zod solo comprueba la forma (formato de cifras y textos). Las reglas de negocio las decide el
 * servidor (constitución VI), y la web NUNCA envía importes calculados (002, FR-014; 005, FR-007):
 * solo unidades, descripción y precio unitario.
 */
import { z } from 'zod'
import { aApi, parsearEntrada, type LineaCalculo } from '../../lib/dinero'

export const MAX_LINEAS = 100

export interface ValorLinea {
  unidades: string
  descripcion: string
  precio_unitario: string
}

/** Lo que tienen en común los formularios con líneas y la casilla de oro de inversión. */
export interface ConLineas {
  lineas: ValorLinea[]
  oro_inversion: boolean
}

export const lineaVacia = (): ValorLinea => ({
  unidades: '1',
  descripcion: '',
  precio_unitario: '',
})

/** Texto del selector para el cliente ya elegido de un borrador. */
export function etiquetaCliente(cliente: { nombre: string; identificacion_numero: string }) {
  return `${cliente.nombre} · ${cliente.identificacion_numero}`
}

export const esquemaLinea = z.object({
  unidades: z.string().refine((v) => {
    const valor = parsearEntrada(v)
    return valor !== null && valor > 0n && valor <= 9_999_999n
  }, 'Unidades no válidas: número mayor que cero con hasta dos decimales.'),
  descripcion: z
    .string()
    .trim()
    .min(1, 'Campo obligatorio.')
    .max(500, 'Como mucho 500 caracteres.'),
  precio_unitario: z
    .string()
    .refine((v) => parsearEntrada(v) !== null, 'Precio no válido: por ejemplo 1.200,50 (sin IVA).'),
})

export const esquemaLineas = z
  .array(esquemaLinea)
  .max(MAX_LINEAS, `Como máximo ${MAX_LINEAS.toString()} líneas.`)

export interface LineaCuerpo {
  unidades: string
  descripcion: string
  precio_unitario: string
}

export function lineasCuerpo(lineas: readonly ValorLinea[]): LineaCuerpo[] {
  return lineas.map((l) => ({
    unidades: aApi(parsearEntrada(l.unidades) ?? 0n),
    descripcion: l.descripcion.trim(),
    precio_unitario: aApi(parsearEntrada(l.precio_unitario) ?? 0n),
  }))
}

/** Líneas válidas para la previsualización (las que aún no se pueden leer, a cero). */
export function lineasCalculo(lineas: readonly ValorLinea[]): LineaCalculo[] {
  return lineas.map((l) => ({
    unidades: parsearEntrada(l.unidades) ?? 0n,
    precio: parsearEntrada(l.precio_unitario) ?? 0n,
  }))
}

/** Campo de línea que corresponde a un error de la API (`lineas` o `lineas.N.campo`), o `null`. */
export function campoDeLinea(
  campo: string,
): 'lineas' | `lineas.${number}.${keyof ValorLinea}` | null {
  if (campo === 'lineas') return campo
  const coincidencia = /^lineas\.(\d+)\.(unidades|descripcion|precio_unitario)$/.exec(campo)
  if (!coincidencia) return null
  const [, indice = '0', nombre = 'unidades'] = coincidencia
  return `lineas.${Number(indice)}.${nombre as keyof ValorLinea}`
}
