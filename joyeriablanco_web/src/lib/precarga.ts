/**
 * Espera a los datos de un modal de documento antes de pintarlo (en el `loader` de su ruta). Así el
 * modal se monta una sola vez, ya con sus datos, y al cerrarlo devuelve el foco a quien lo abrió
 * (FR-039): si primero se pintara la carga y después otro modal con el contenido, se perdería.
 *
 * Los errores no se propagan: quedan en la caché de consultas y el modal los muestra con su propio
 * mensaje.
 */
export async function precargar(...cargas: readonly Promise<unknown>[]): Promise<void> {
  await Promise.allSettled(cargas)
}
