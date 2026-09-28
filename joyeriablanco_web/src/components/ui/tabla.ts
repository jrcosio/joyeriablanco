/**
 * Clases compartidas por las tablas con acciones por fila (DESIGN.md §Data Tables, FR-059, R-22):
 * la tabla se desplaza dentro de su tarjeta y la columna de acciones queda fija a la derecha, con
 * el fondo sólido de su fila para tapar lo que pasa por debajo. Las filas llevan `group`.
 */
export const tablaDesplazable = 'overflow-x-auto'
export const accionesCabecera = 'sticky right-0 w-px whitespace-nowrap bg-surface-container'
export const accionesCelda =
  'sticky right-0 w-px whitespace-nowrap bg-surface-container-low transition-colors ' +
  'group-hover:bg-surface-container-high'
