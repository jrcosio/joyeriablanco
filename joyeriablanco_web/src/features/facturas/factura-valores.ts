/**
 * Valores del formulario de factura, validación de forma y cuerpo para la API.
 *
 * Zod solo comprueba la forma (formato de cifras y textos). Las reglas de negocio (cliente
 * facturable, fechas, IVA admitido, totales) las decide el servidor (constitución VI), y la web
 * NUNCA envía importes calculados (FR-014): solo unidades, descripción y precio unitario.
 */
import { z } from 'zod'
import type { BorradorEntrada, BorradorSalida, FacturaEntrada } from '../../api/tipos'
import { desdeApi, formatearCantidad } from '../../lib/dinero'
import {
  campoDeLinea,
  esquemaLineas,
  lineasCuerpo as lineasCuerpoComun,
  lineaVacia,
  type ValorLinea,
} from '../documentos/documento-valores'

// Lo común con los presupuestos vive en `documentos/documento-valores.ts` (005, R-13).
export {
  etiquetaCliente,
  lineasCalculo,
  lineaVacia,
  MAX_LINEAS,
  type ValorLinea,
} from '../documentos/documento-valores'

export interface ValoresFactura {
  fecha_expedicion: string
  cliente_id: string | null
  lineas: ValorLinea[]
  /** «Sin IVA (oro de inversión)»: toda la factura exenta (FR-052). */
  oro_inversion: boolean
}

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

export const esquema = z.object({
  fecha_expedicion: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Fecha no válida.'),
  cliente_id: z.string().nullable(),
  lineas: esquemaLineas,
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
  return lineasCuerpoComun(lineas)
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

/** Campo del formulario que corresponde a un error de la API, o `null` si no hay ninguno. */
export function campoDelServidor(
  campo: string,
): 'fecha_expedicion' | 'cliente_id' | 'lineas' | `lineas.${number}.${keyof ValorLinea}` | null {
  if (campo === 'fecha_expedicion' || campo === 'cliente_id') return campo
  return campoDeLinea(campo)
}
