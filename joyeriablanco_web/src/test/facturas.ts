import { http, HttpResponse } from 'msw'
import type { BorradorSalida, FacturaSalida, ParametrosFacturacionSalida } from '../api/tipos'
import { server } from './msw'

export const MENCION_ORO = 'Operación exenta de IVA (art. 140 bis.Uno.1.º de la Ley 37/1992)'
export const IBAN_DEMO = 'ES9121000418450200051332'

export const PARAMETROS: ParametrosFacturacionSalida = {
  iva_por_defecto: '21.00',
  emision_posible: true,
  faltan: [],
  proximo_numero: 'FAC-2026-0006',
  hoy: '2026-09-29',
  fecha_minima: '2024-10-28',
  mencion_exencion_oro_inversion: MENCION_ORO,
}

/** La API responde a los parámetros del modal de factura y al listado de detrás (vacío). */
export function conFacturacion(parametros: ParametrosFacturacionSalida = PARAMETROS): void {
  server.use(
    http.get('*/api/v1/facturas/parametros', () => HttpResponse.json(parametros)),
    http.get('*/api/v1/facturas', () =>
      HttpResponse.json({ elementos: [], total: 0, pagina: 1, tamano: 25 }),
    ),
  )
}

/** Factura emitida de la captura: 1.290,00 € de base y 1.560,90 € de total. */
export function crearFactura(parcial: Partial<FacturaSalida> = {}): FacturaSalida {
  return {
    id: '0192f0c0-0000-7000-8000-0000000f0001',
    num_serie: 'FAC-2026-0005',
    tipo_factura: 'F1',
    tipo_rectificativa: null,
    estado: 'vigente',
    fecha_expedicion: '2026-09-29',
    fecha_operacion: null,
    emisor: {
      nombre: 'Joyería de Pruebas S.L.',
      nif: 'B00000000',
      direccion: 'Calle Mayor, 1',
      codigo_postal: '29001',
      localidad: 'Málaga',
      iban: null,
      provincia: 'Málaga',
    },
    cliente: {
      id: '0192f0c0-0000-7000-8000-00000000c001',
      nombre: 'María López García',
      identificacion_pais: 'ES',
      identificacion_tipo: 'NIF',
      identificacion_numero: '12345678Z',
      direccion: 'Calle Serrano, 45',
      codigo_postal: '29005',
      localidad: 'Málaga',
      provincia: 'Málaga',
      pais: 'ES',
    },
    lineas: [
      {
        orden: 1,
        unidades: '1.00',
        descripcion: 'Anillo',
        precio_unitario: '1200.00',
        tipo_iva: '21.00',
        importe: '1200.00',
      },
      {
        orden: 2,
        unidades: '2.00',
        descripcion: 'Ajuste',
        precio_unitario: '45.00',
        tipo_iva: '21.00',
        importe: '90.00',
      },
    ],
    totales: {
      desglose: [{ tipo_iva: '21.00', base: '1290.00', cuota: '270.90' }],
      base_total: '1290.00',
      cuota_total: '270.90',
      importe_total: '1560.90',
    },
    oro_inversion: false,
    mencion_exencion: null,
    descripcion_operacion: 'Anillo; Ajuste',
    rectifica_a: null,
    sustituye_a: null,
    vigente_actual: null,
    correcciones: [],
    emitida_en: '2026-09-29T08:30:00Z',
    emitida_por: { id: 'u1', nombre: 'Ana García', eliminado: false },
    registros: [
      {
        tipo: 'alta',
        secuencia: 5,
        huella: '3C464DAF61ACB827C65FDA19F352A4E3BDC2C640E9E9FC4CC058073F38F12F60',
        fecha_hora_huso_gen: '2026-09-29T10:30:00+02:00',
        estado_remision: 'pendiente',
      },
    ],
    ...parcial,
  }
}

/** Factura de oro de inversión sin IVA (FR-052): un lingote de 7.450,00 €, con el IBAN. */
export function crearFacturaExenta(parcial: Partial<FacturaSalida> = {}): FacturaSalida {
  const base = crearFactura()
  return crearFactura({
    num_serie: 'FAC-2026-0007',
    emisor: { ...base.emisor, iban: IBAN_DEMO },
    lineas: [
      {
        orden: 1,
        unidades: '1.00',
        descripcion: 'Lingote de oro 100 g',
        precio_unitario: '7450.00',
        tipo_iva: null,
        importe: '7450.00',
      },
    ],
    totales: {
      desglose: [{ tipo_iva: null, base: '7450.00', cuota: '0.00' }],
      base_total: '7450.00',
      cuota_total: '0.00',
      importe_total: '7450.00',
    },
    oro_inversion: true,
    mencion_exencion: MENCION_ORO,
    descripcion_operacion: 'Lingote de oro 100 g',
    ...parcial,
  })
}

/** Borrador de factura de María, con una línea (002); `presupuesto_origen` si procede de uno (005). */
export function crearBorradorFactura(parcial: Partial<BorradorSalida> = {}): BorradorSalida {
  return {
    id: '0192f0c0-0000-7000-8000-0000000b0001',
    version: 3,
    fecha_expedicion: '2026-09-28',
    cliente: {
      id: '0192f0c0-0000-7000-8000-00000000c001',
      nombre: 'María López García',
      identificacion_pais: 'ES',
      identificacion_tipo: 'NIF',
      identificacion_numero: '12345678Z',
      direccion: 'Calle Serrano, 45',
      codigo_postal: '29005',
      localidad: 'Málaga',
      provincia: 'Málaga',
      pais: 'ES',
      activo: true,
    },
    lineas: [
      {
        orden: 1,
        unidades: '1.00',
        descripcion: 'Anillo',
        precio_unitario: '1200.00',
        importe: '1200.00',
      },
    ],
    totales_previstos: {
      desglose: [{ tipo_iva: '21.00', base: '1200.00', cuota: '252.00' }],
      base_total: '1200.00',
      cuota_total: '252.00',
      importe_total: '1452.00',
    },
    tipo_iva_previsto: '21.00',
    oro_inversion: false,
    mencion_exencion: null,
    creado_en: '2026-09-28T08:00:00Z',
    creado_por: { id: 'u1', nombre: 'Ana García', eliminado: false },
    actualizado_en: '2026-09-28T08:00:00Z',
    actualizado_por: { id: 'u1', nombre: 'Ana García', eliminado: false },
    ...parcial,
  }
}
