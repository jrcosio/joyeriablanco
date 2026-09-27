/** Une clases condicionales (sin dependencias). */
export function cx(...clases: (string | false | null | undefined)[]): string {
  return clases.filter(Boolean).join(' ')
}
