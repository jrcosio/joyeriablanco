/**
 * Valores del formulario de factura, validación de forma y cuerpo para la API.
 *
 * Zod solo comprueba la forma (formato de cifras y textos). Las reglas de negocio (cliente
 * facturable, fechas, IVA admitido, totales) las decide el servidor (constitución VI), y la web
 * NUNCA envía importes calculados (FR-014): solo unidades, descripción y precio unitario.
 */
import { z } from 'zod'
import type { BorradorEntrada, BorradorSalida, FacturaEntrada } from '../../api/tipos'
import {
  aApi,
  desdeApi,
  formatearCantidad,
  parsearEntrada,
  type LineaCalculo,
} from '../../lib/dinero'

export const MAX_LINEAS = 100

export interface ValorLinea {
  unidades: string
  descripcion: string
  precio_unitario: string
}

export interface ValoresFactura {
  fecha_expedicion: string
  cliente_id: string | null
  lineas: ValorLinea[]
  /** «Sin IVA (oro de inversión)»: toda la factura exenta (FR-052). */
  oro_inversion: boolean
}

export const lineaVacia = (): ValorLinea => ({
  unidades: '1',
  descripcion: '',
  precio_unitario: '',
})

export function valoresIniciales(hoy: string): ValoresFactura {
  return { fecha_expedicion: hoy, cliente_id: null, lineas: [lineaVacia()], oro_inversion: false }
}

/** Valores del formulario a partir de un borrador guardado, con las cifras en formato español. */
export function valoresDelBorrador(borrador: BorradorSalida): ValoresFactura {
  return {
    fecha_expedicion: borrador.fecha_expedicion,
    cliente_id: borrador.cliente?.id ?? null,
    lineas: borrador.lineas.map((l) => ({
      unidades: formatearCantidad(desdeApi(l.unidades)),
      descripcion: l.descripcion,
      precio_unitario: formatearCantidad(desdeApi(l.precio_unitario)),
    })),
    oro_inversion: borrador.oro_inversion,
  }
}

/** Texto del selector para el cliente ya elegido de un borrador. */
export function etiquetaCliente(cliente: { nombre: string; identificacion_numero: string }) {
  return `${cliente.nombre} · ${cliente.identificacion_numero}`
}

const linea = z.object({
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

export const esquema = z.object({
  fecha_expedicion: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Fecha no válida.'),
  cliente_id: z.string().nullable(),
  lineas: z.array(linea).max(MAX_LINEAS, `Como máximo ${MAX_LINEAS.toString()} líneas.`),
  oro_inversion: z.boolean(),
})

/** Requisitos que solo se exigen al emitir, no al guardar un borrador (FR-011). */
export function erroresParaEmitir(
  valores: ValoresFactura,
): { campo: 'cliente_id' | 'lineas'; mensaje: string }[] {
  const errores: { campo: 'cliente_id' | 'lineas'; mensaje: string }[] = []
  if (!valores.cliente_id) errores.push({ campo: 'cliente_id', mensaje: 'Elige el cliente.' })
  if (valores.lineas.length === 0) {
    errores.push({ campo: 'lineas', mensaje: 'La factura debe tener al menos una línea.' })
  }
  return errores
}

export function lineasCuerpo(lineas: readonly ValorLinea[]): FacturaEntrada['lineas'] {
  return lineas.map((l) => ({
    unidades: aApi(parsearEntrada(l.unidades) ?? 0n),
    descripcion: l.descripcion.trim(),
    precio_unitario: aApi(parsearEntrada(l.precio_unitario) ?? 0n),
  }))
}

/**
 * Cuerpo de un borrador: puede ir sin cliente o sin líneas (FR-011). Nunca lleva totales. La
 * casilla va siempre, porque al editar o emitir es obligatoria (research R-21).
 */
export function aCuerpoBorrador(
  valores: ValoresFactura,
): BorradorEntrada & { oro_inversion: boolean } {
  return {
    fecha_expedicion: valores.fecha_expedicion,
    cliente_id: valores.cliente_id,
    lineas: lineasCuerpo(valores.lineas),
    oro_inversion: valores.oro_inversion,
  }
}

export function aCuerpo(valores: ValoresFactura): FacturaEntrada {
  if (!valores.cliente_id) throw new Error('Falta el cliente')
  return {
    fecha_expedicion: valores.fecha_expedicion,
    cliente_id: valores.cliente_id,
    lineas: lineasCuerpo(valores.lineas),
    oro_inversion: valores.oro_inversion,
  }
}

/** Líneas válidas para la previsualización (las que aún no se pueden leer, a cero). */
export function lineasCalculo(lineas: readonly ValorLinea[]): LineaCalculo[] {
  return lineas.map((l) => ({
    unidades: parsearEntrada(l.unidades) ?? 0n,
    precio: parsearEntrada(l.precio_unitario) ?? 0n,
  }))
}

/** Campo del formulario que corresponde a un error de la API, o `null` si no hay ninguno. */
export function campoDelServidor(
  campo: string,
): 'fecha_expedicion' | 'cliente_id' | 'lineas' | `lineas.${number}.${keyof ValorLinea}` | null {
  if (campo === 'fecha_expedicion' || campo === 'cliente_id' || campo === 'lineas') return campo
  const coincidencia = /^lineas\.(\d+)\.(unidades|descripcion|precio_unitario)$/.exec(campo)
  if (!coincidencia) return null
  const [, indice = '0', nombre = 'unidades'] = coincidencia
  return `lineas.${Number(indice)}.${nombre as keyof ValorLinea}`
}
