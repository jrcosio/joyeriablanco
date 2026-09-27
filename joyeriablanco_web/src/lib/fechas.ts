/** Formatos de fecha en español de España, en hora peninsular (FR-038, FR-060). */
export const ZONA_HORARIA = 'Europe/Madrid'

const fechaLargaFmt = new Intl.DateTimeFormat('es-ES', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  year: 'numeric',
  timeZone: ZONA_HORARIA,
})

const fechaHoraFmt = new Intl.DateTimeFormat('es-ES', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  timeZone: ZONA_HORARIA,
})

const claveDiaFmt = new Intl.DateTimeFormat('en-CA', { timeZone: ZONA_HORARIA })

function capitalizar(texto: string): string {
  return texto.charAt(0).toLocaleUpperCase('es-ES') + texto.slice(1)
}

/** "Martes, 27 de mayo de 2025" */
export function fechaLarga(fecha: Date): string {
  return capitalizar(fechaLargaFmt.format(fecha))
}

/** "27/05/2025, 14:32" */
export function fechaHora(fecha: Date | string): string {
  return fechaHoraFmt.format(typeof fecha === 'string' ? new Date(fecha) : fecha)
}

/** Clave AAAA-MM-DD del día en hora peninsular (para detectar el cambio de día). */
export function claveDia(fecha: Date): string {
  return claveDiaFmt.format(fecha)
}
