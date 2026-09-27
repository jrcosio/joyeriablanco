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

/** Desfase de Europe/Madrid (p. ej. "+02:00") en una fecha AAAA-MM-DD. */
function desfaseMadrid(fecha: string): string {
  const instante = new Date(`${fecha}T12:00:00Z`)
  const partes = new Intl.DateTimeFormat('en-US', {
    timeZone: ZONA_HORARIA,
    timeZoneName: 'longOffset',
  }).formatToParts(instante)
  const nombre = partes.find((p) => p.type === 'timeZoneName')?.value ?? 'GMT+01:00'
  return nombre === 'GMT' ? '+00:00' : nombre.replace('GMT', '')
}

/** Inicio del día (00:00) en hora peninsular, en ISO con zona. */
export function inicioDia(fecha: string): string {
  return `${fecha}T00:00:00${desfaseMadrid(fecha)}`
}

/** Fin del día (23:59:59.999) en hora peninsular, en ISO con zona. */
export function finDia(fecha: string): string {
  return `${fecha}T23:59:59.999${desfaseMadrid(fecha)}`
}
