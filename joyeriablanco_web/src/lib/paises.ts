/** Nombres de países en español (Intl.DisplayNames) y orden con España primero (FR-060). */
const nombres = new Intl.DisplayNames(['es-ES'], { type: 'region', fallback: 'code' })

export function nombrePais(codigo: string): string {
  try {
    return nombres.of(codigo.toUpperCase()) ?? codigo
  } catch {
    return codigo
  }
}

export interface OpcionPais {
  codigo: string
  nombre: string
}

export function opcionesPaises(codigos: readonly string[]): OpcionPais[] {
  const opciones = codigos.map((codigo) => ({ codigo, nombre: nombrePais(codigo) }))
  opciones.sort((a, b) => {
    if (a.codigo === 'ES') return -1
    if (b.codigo === 'ES') return 1
    return a.nombre.localeCompare(b.nombre, 'es-ES')
  })
  return opciones
}
