import { http, HttpResponse } from 'msw'
import type {
  ParametrosPresupuestoSalida,
  PresupuestoResumenSalida,
  PresupuestoSalida,
} from '../api/tipos'
import { crearFactura, MENCION_ORO } from './facturas'
import { server } from './msw'

/** Datos de prueba de presupuestos (005): parámetros del modal, presupuestos y filas. */
export const PARAMETROS_PRESUPUESTO: ParametrosPresupuestoSalida = {
  iva_por_defecto: '21.00',
  emision_posible: true,
  faltan: [],
  proximo_numero: 'PRE-2026-0004',
  hoy: '2026-09-29',
  fecha_minima: '2024-10-28',
  validez_dias: 30,
  mencion_exencion_oro_inversion: MENCION_ORO,
}

/** La API responde a los parámetros del modal y al listado de detrás (vacío). */
export function conPresupuestos(
  parametros: ParametrosPresupuestoSalida = PARAMETROS_PRESUPUESTO,
): void {
  server.use(
    http.get('*/api/v1/presupuestos/parametros', () => HttpResponse.json(parametros)),
    http.get('*/api/v1/presupuestos', () =>
      HttpResponse.json({ elementos: [], total: 0, pagina: 1, tamano: 25 }),
    ),
  )
}

/** Presupuesto emitido con las líneas de la factura de prueba: 1.560,90 € de total. */
export function crearPresupuesto(parcial: Partial<PresupuestoSalida> = {}): PresupuestoSalida {
  const factura = crearFactura()
  return {
    id: '0192f0c0-0000-7000-8000-0000000e0003',
    num_serie: 'PRE-2026-0003',
    estado: 'pendiente',
    fecha: '2026-09-29',
    valido_hasta: '2026-10-29',
    emisor: factura.emisor,
    cliente: factura.cliente,
    lineas: factura.lineas,
    totales: factura.totales,
    oro_inversion: false,
    mencion_exencion: null,
    sustituye_a: null,
    vigente_actual: null,
    cierre: null,
    borrador_factura: null,
    emitido_en: '2026-09-29T08:30:00Z',
    emitido_por: { id: 'u1', nombre: 'Ana García', eliminado: false },
    ...parcial,
  }
}

export function filaPresupuesto(
  parcial: Partial<PresupuestoResumenSalida> = {},
): PresupuestoResumenSalida {
  return {
    tipo_documento: 'presupuesto',
    id: '0192f0c0-0000-7000-8000-0000000e0003',
    num_serie: 'PRE-2026-0003',
    fecha: '2026-09-29',
    valido_hasta: '2026-10-29',
    cliente_nombre: 'María López García',
    identificacion: '12345678Z',
    base: '1290.00',
    cuota: '270.90',
    total: '1560.90',
    estado: 'pendiente',
    oro_inversion: false,
    ...parcial,
  }
}
