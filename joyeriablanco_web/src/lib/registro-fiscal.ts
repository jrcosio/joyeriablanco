/** Textos del registro fiscal (004): tipos de evento de F-17 (`TipoEventoType`), en español. */
import type { TipoEventoSif } from '../api/tipos'

export const TIPOS_EVENTO_SIF: Record<TipoEventoSif, string> = {
  '01': 'Inicio del funcionamiento',
  '02': 'Fin del funcionamiento',
  '03': 'Comprobación de los registros de facturación',
  '04': 'Anomalía en los registros de facturación',
  '05': 'Comprobación de los registros de evento',
  '06': 'Anomalía en los registros de evento',
  '08': 'Exportación de registros de facturación',
  '09': 'Exportación de registros de evento',
  '10': 'Resumen de eventos',
}

export type PestanaRegistroFiscal = 'eventos' | 'cadena' | 'comprobar' | 'exportar'
