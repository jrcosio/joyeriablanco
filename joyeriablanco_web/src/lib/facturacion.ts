/** Textos y catálogos de facturación compartidos por Configuración y el modal de factura. */

/** Lo que falta para poder emitir (FR-004), con el nombre que ve el usuario. */
export const FALTA_PARA_EMITIR: Record<string, string> = {
  modalidad: 'Modalidad del sistema de facturación',
  'emisor.nombre': 'Nombre o razón social del emisor',
  'emisor.nif': 'NIF del emisor',
  'emisor.direccion': 'Dirección del emisor',
  'emisor.codigo_postal': 'Código postal del emisor',
  'emisor.localidad': 'Localidad del emisor',
}

export function textoFalta(clave: string): string {
  return FALTA_PARA_EMITIR[clave] ?? clave
}

export const MODALIDADES: readonly { id: string; label: string }[] = [
  { id: '', label: 'Sin decidir (pendiente de la asesoría)' },
  { id: 'verifactu', label: 'VERI*FACTU' },
  { id: 'no_verifactu', label: 'No VERI*FACTU' },
]

/** «21.00» → «21»; «12.50» → «12,5»: el tipo como se escribe en el campo de Configuración. */
export function tipoIvaATexto(tipo: string): string {
  return tipo
    .replace(/\.00$/, '')
    .replace(/(\.\d)0$/, '$1')
    .replace('.', ',')
}

/** «21.00» → «21 %». */
export function textoTipoIva(tipo: string): string {
  return `${tipoIvaATexto(tipo)} %`
}

/** Tipos de la lista oficial (F-3 §15.1) para el aviso: «0, 4, 10 y 21» (research R-20). */
export function listaTiposIva(tipos: readonly string[]): string {
  const textos = tipos.map(tipoIvaATexto)
  const ultimo = textos.pop()
  if (ultimo === undefined) return ''
  return textos.length ? `${textos.join(', ')} y ${ultimo}` : ultimo
}

/** IBAN agrupado de cuatro en cuatro, en mayúsculas y sin espacios de más (research R-22). */
export function formatearIban(texto: string): string {
  return (
    texto
      .replace(/\s+/g, '')
      .toUpperCase()
      .match(/.{1,4}/g)
      ?.join(' ') ?? ''
  )
}

/** IBAN como lo guarda la API: sin espacios y en mayúsculas. */
export function normalizarIban(texto: string): string {
  return texto.replace(/\s+/g, '').toUpperCase()
}

/** Motivos de «Modificar» (FR-024), con el texto que ve el administrador. */
export const MOTIVOS_MODIFICACION = {
  no_debio_emitirse: 'La factura no debió emitirse o no llegó a entregarse al cliente',
  factura_entregada: 'Hay que corregir una factura ya entregada',
} as const

/** Causas de una rectificativa (FR-024; F-9): R1 o R4. */
export const CAUSAS_RECTIFICACION = {
  devolucion_o_precio:
    'Devolución, descuento o cambio de precio posterior a la venta, o IVA mal aplicado',
  error_datos: 'Error en datos o importes de la factura',
} as const

/** Tipo de cada corrección en el historial (FR-026). */
export const TIPOS_CORRECCION = {
  anulacion: 'Anulación',
  anulacion_y_reemision: 'Anulación y reemisión',
  rectificacion_sustitucion: 'Rectificación por sustitución',
} as const

/**
 * Tipo de IVA de una factura emitida (todas sus líneas llevan el mismo, FR-013), o `null` si va
 * sin IVA por oro de inversión (FR-052).
 */
export function tipoIvaDe(factura: {
  oro_inversion: boolean
  lineas: readonly { tipo_iva: string | null }[]
  totales: { desglose: readonly { tipo_iva: string | null }[] }
}): string | null {
  if (factura.oro_inversion) return null
  return factura.lineas[0]?.tipo_iva ?? factura.totales.desglose[0]?.tipo_iva ?? null
}
