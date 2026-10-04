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

/** F-17, `TipoAnomaliaType`: las descripciones oficiales del esquema (research R-10). */
export const TEXTO_ANOMALIA: Record<string, string> = {
  '01': 'Integridad-huella',
  '02': 'Integridad-firma',
  '03': 'Integridad - Otros',
  '04': 'Registro no primero con el anterior no anotado o inexistente',
  '05': 'Registro no último con el posterior no anotado o inexistente',
  '06': 'Trazabilidad-cadena-registro - Otros',
  '07': 'La huella no coincide con la «huella del anterior» del posterior',
  '08': 'La «huella del anterior» no coincide con la huella del anterior',
  '09': 'Trazabilidad-cadena-huella - Otros',
  '10': 'Trazabilidad-cadena - Otros',
  '11': 'Fecha y hora anteriores a las del registro anterior',
  '12': 'Fecha y hora posteriores a las del registro posterior',
  '13': 'Fecha y hora de generación posteriores a la hora actual',
  '14': 'Trazabilidad-fechas - Otros',
  '15': 'Trazabilidad - Otros',
  '90': 'Otros',
}
