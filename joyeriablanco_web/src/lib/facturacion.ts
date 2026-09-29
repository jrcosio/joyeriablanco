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

/**
 * Lista L8A de DsRegistroVeriFactu.xlsx v1.0 (claves de régimen del IVA), con el texto oficial
 * abreviado. La joyería usa la 01 (Clarifications de 002).
 */
export const CLAVES_REGIMEN: readonly { id: string; label: string }[] = [
  { id: '01', label: '01 · Operación de régimen general' },
  { id: '02', label: '02 · Exportación' },
  { id: '03', label: '03 · Régimen especial de bienes usados, arte, antigüedades y colección' },
  { id: '04', label: '04 · Régimen especial del oro de inversión' },
  { id: '05', label: '05 · Régimen especial de las agencias de viajes' },
  { id: '06', label: '06 · Régimen especial grupo de entidades en IVA' },
  { id: '07', label: '07 · Régimen especial del criterio de caja' },
  { id: '08', label: '08 · Operaciones sujetas al IPSI o al IGIC' },
  { id: '09', label: '09 · Agencias de viaje que actúan como mediadoras' },
  { id: '10', label: '10 · Cobros por cuenta de terceros' },
  { id: '11', label: '11 · Arrendamiento de local de negocio' },
  { id: '14', label: '14 · IVA pendiente de devengo en certificaciones de obra' },
  { id: '15', label: '15 · IVA pendiente de devengo en tracto sucesivo' },
  { id: '17', label: '17 · Regímenes de ventanilla única (OSS e IOSS)' },
  { id: '18', label: '18 · Recargo de equivalencia' },
  { id: '19', label: '19 · Régimen especial de agricultura, ganadería y pesca' },
  { id: '20', label: '20 · Régimen simplificado' },
]

export const MODALIDADES: readonly { id: string; label: string }[] = [
  { id: '', label: 'Sin decidir (pendiente de la asesoría)' },
  { id: 'verifactu', label: 'VERI*FACTU' },
  { id: 'no_verifactu', label: 'No VERI*FACTU' },
]

/** «21.00» → «21 %». */
export function textoTipoIva(tipo: string): string {
  const numero = tipo
    .replace(/\.00$/, '')
    .replace(/(\.\d)0$/, '$1')
    .replace('.', ',')
  return `${numero} %`
}
