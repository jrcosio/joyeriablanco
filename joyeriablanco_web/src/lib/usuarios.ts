/** Nombre visible de un usuario referenciado; si fue eliminado, con la marca (FR-061). */
export function nombreConEstado(usuario: { nombre: string; eliminado: boolean }): string {
  return usuario.eliminado ? `${usuario.nombre} (eliminado)` : usuario.nombre
}
