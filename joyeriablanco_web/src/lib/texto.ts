/**
 * Iniciales del menú de usuario (FR-056): primera letra de las dos primeras palabras o, si solo
 * hay una palabra, sus dos primeras letras, en mayúsculas.
 */
export function iniciales(nombre: string): string {
  const palabras = nombre.trim().split(/\s+/).filter(Boolean)
  const [primera, segunda] = palabras
  if (!primera) return '?'
  const letras = segunda
    ? `${Array.from(primera)[0] ?? ''}${Array.from(segunda)[0] ?? ''}`
    : Array.from(primera).slice(0, 2).join('')
  return letras.toLocaleUpperCase('es-ES')
}

/** Normaliza para comparar sin tildes ni mayúsculas. */
export function normalizar(texto: string): string {
  return texto
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLocaleLowerCase('es-ES')
}
