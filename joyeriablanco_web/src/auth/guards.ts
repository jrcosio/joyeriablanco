/** Guardas de ruta (comodidad de la web: la API es quien decide, FR-013). */
import type { QueryClient } from '@tanstack/react-query'
import { redirect } from '@tanstack/react-router'
import type { SesionSalida } from '../api/tipos'
import { sesionQuery } from './session'

interface ContextoGuarda {
  context: { queryClient: QueryClient }
  location: { href: string }
}

/** Exige sesión; si la contraseña es temporal, obliga a cambiarla (FR-009). */
export async function requireSession({
  context,
  location,
}: ContextoGuarda): Promise<{ sesion: SesionSalida }> {
  const sesion = await context.queryClient.query(sesionQuery)
  if (!sesion) {
    throw redirect({ to: '/acceso', search: { volver: location.href } })
  }
  if (sesion.usuario.contrasena_temporal) {
    throw redirect({ to: '/cambiar-contrasena' })
  }
  return { sesion }
}

export function requireAdmin(sesion: SesionSalida): void {
  if (sesion.usuario.rol !== 'administrador') {
    throw redirect({ to: '/acceso-denegado' })
  }
}
