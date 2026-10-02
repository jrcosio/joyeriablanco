/**
 * Valores del formulario de presupuesto, validación de forma y cuerpo para la API (005).
 *
 * Como en la factura: Zod solo comprueba la forma, las reglas las decide el servidor
 * (constitución VI) y la web NUNCA envía importes calculados (FR-007).
 */
import { z } from 'zod'
import type {
  BorradorPresupuestoEntrada,
  BorradorPresupuestoSalida,
  PresupuestoEntrada,
  PresupuestoSalida,
} from '../../api/tipos'
import { desdeApi, formatearCantidad } from '../../lib/dinero'
import { sumarDias } from '../../lib/fechas'
import {
  campoDeLinea,
  esquemaLineas,
  lineasCuerpo,
  lineaVacia,
  type ValorLinea,
} from '../documentos/documento-valores'

export interface ValoresPresupuesto {
  fecha: string
  valido_hasta: string
  cliente_id: string | null
  lineas: ValorLinea[]
  /** «Sin IVA (oro de inversión)»: todo el presupuesto exento (FR-007). */
  oro_inversion: boolean
}

export function valoresIniciales(hoy: string, validezDias: number): ValoresPresupuesto {
  return {
    fecha: hoy,
    valido_hasta: sumarDias(hoy, validezDias),
    cliente_id: null,
    lineas: [lineaVacia()],
    oro_inversion: false,
  }
}

function lineasDe(
  lineas: readonly { unidades: string; descripcion: string; precio_unitario: string }[],
) {
  return lineas.map((l) => ({
    unidades: formatearCantidad(desdeApi(l.unidades)),
    descripcion: l.descripcion,
    precio_unitario: formatearCantidad(desdeApi(l.precio_unitario)),
  }))
}

/** Valores del formulario a partir de un borrador guardado, con las cifras en formato español. */
export function valoresDelBorrador(borrador: BorradorPresupuestoSalida): ValoresPresupuesto {
  return {
    fecha: borrador.fecha,
    valido_hasta: borrador.valido_hasta,
    cliente_id: borrador.cliente?.id ?? null,
    lineas: lineasDe(borrador.lineas),
    oro_inversion: borrador.oro_inversion,
  }
}

/**
 * Valores para «Modificar» un presupuesto emitido (FR-015): sus datos con la fecha de hoy. La
 * validez es la del original o, si ya es anterior a hoy, hoy más la validez por defecto.
 */
export function valoresDelPresupuesto(
  presupuesto: PresupuestoSalida,
  hoy: string,
  validezDias: number,
): ValoresPresupuesto {
  return {
    fecha: hoy,
    valido_hasta:
      presupuesto.valido_hasta < hoy ? sumarDias(hoy, validezDias) : presupuesto.valido_hasta,
    cliente_id: presupuesto.cliente.id,
    lineas: lineasDe(presupuesto.lineas),
    oro_inversion: presupuesto.oro_inversion,
  }
}

const FECHA = /^\d{4}-\d{2}-\d{2}$/

export const esquema = z
  .object({
    fecha: z.string().regex(FECHA, 'Fecha no válida.'),
    valido_hasta: z.string().regex(FECHA, 'Fecha no válida.'),
    cliente_id: z.string().nullable(),
    lineas: esquemaLineas,
    oro_inversion: z.boolean(),
  })
  // Fechas AAAA-MM-DD: se comparan como texto (FR-009).
  .refine((v) => v.valido_hasta >= v.fecha, {
    path: ['valido_hasta'],
    message: '«Válido hasta» no puede ser anterior a la fecha.',
  })

/** Requisitos que solo se exigen al emitir, no al guardar un borrador (FR-006). */
export function erroresParaEmitir(
  valores: ValoresPresupuesto,
): { campo: 'cliente_id' | 'lineas'; mensaje: string }[] {
  const errores: { campo: 'cliente_id' | 'lineas'; mensaje: string }[] = []
  if (!valores.cliente_id) errores.push({ campo: 'cliente_id', mensaje: 'Elige el cliente.' })
  if (valores.lineas.length === 0) {
    errores.push({ campo: 'lineas', mensaje: 'El presupuesto debe tener al menos una línea.' })
  }
  return errores
}

/** Cuerpo de un borrador: puede ir sin cliente o sin líneas (FR-012). Nunca lleva totales. */
export function aCuerpoBorrador(
  valores: ValoresPresupuesto,
): BorradorPresupuestoEntrada & { oro_inversion: boolean } {
  return {
    fecha: valores.fecha,
    valido_hasta: valores.valido_hasta,
    cliente_id: valores.cliente_id,
    lineas: lineasCuerpo(valores.lineas),
    oro_inversion: valores.oro_inversion,
  }
}

export function aCuerpo(valores: ValoresPresupuesto): PresupuestoEntrada {
  if (!valores.cliente_id) throw new Error('Falta el cliente')
  return {
    fecha: valores.fecha,
    valido_hasta: valores.valido_hasta,
    cliente_id: valores.cliente_id,
    lineas: lineasCuerpo(valores.lineas),
    oro_inversion: valores.oro_inversion,
  }
}

/** Campo del formulario que corresponde a un error de la API, o `null` si no hay ninguno. */
export function campoDelServidor(
  campo: string,
):
  | 'fecha'
  | 'valido_hasta'
  | 'cliente_id'
  | 'lineas'
  | `lineas.${number}.${keyof ValorLinea}`
  | null {
  if (campo === 'fecha' || campo === 'valido_hasta' || campo === 'cliente_id') return campo
  return campoDeLinea(campo)
}
