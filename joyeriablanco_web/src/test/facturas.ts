import { http, HttpResponse } from 'msw'
import type { FacturaSalida, ParametrosFacturacionSalida } from '../api/tipos'
import { server } from './msw'

export const PARAMETROS: ParametrosFacturacionSalida = {
  iva_por_defecto: '21.00',
  emision_posible: true,
  faltan: [],
  proximo_numero: 'FAC-2026-0006',
  hoy: '2026-09-29',
  fecha_minima: '2024-10-28',
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
