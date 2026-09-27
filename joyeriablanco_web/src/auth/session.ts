/**
 * Sesión del usuario en la web. La cookie es HttpOnly: la web solo conoce lo que devuelve
 * `GET /api/v1/sesion` (usuario, rol y token CSRF).
 */
import { queryOptions, useQuery, type QueryClient } from '@tanstack/react-query'
import { api, ApiError, setCsrfToken, unwrap } from '../api/client'
import type { SesionSalida } from '../api/tipos'

export const SESION_KEY = ['sesion'] as const

export async function obtenerSesion(): Promise<SesionSalida | null> {
  try {
    const sesion = await unwrap(api.GET('/api/v1/sesion'))
    setCsrfToken(sesion.csrf_token)
    return sesion
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      setCsrfToken(null)
      return null
    }
    throw error
  }
}

export const sesionQuery = queryOptions({
  queryKey: SESION_KEY,
  queryFn: obtenerSesion,
  staleTime: 60_000,
})

/** Sesión actual (dentro de las rutas protegidas siempre existe). */
export function useSesion(): SesionSalida {
  const { data } = useQuery(sesionQuery)
  if (!data) throw new Error('useSesion requiere una sesión iniciada')
  return data
}

export async function iniciarSesion(
  queryClient: QueryClient,
  credenciales: { nombre_usuario: string; contrasena: string },
): Promise<SesionSalida> {
  const sesion = await unwrap(api.POST('/api/v1/sesion', { body: credenciales }))
  setCsrfToken(sesion.csrf_token)
  queryClient.setQueryData(SESION_KEY, sesion)
  return sesion
}

/** Olvida todo lo cacheado (datos de negocio incluidos) al salir o al perder la sesión. */
export function olvidarSesion(queryClient: QueryClient): void {
  setCsrfToken(null)
  queryClient.removeQueries({ predicate: (q) => q.queryKey[0] !== SESION_KEY[0] })
  queryClient.setQueryData(SESION_KEY, null)
}

export async function cerrarSesion(queryClient: QueryClient): Promise<void> {
  try {
    await unwrap(api.DELETE('/api/v1/sesion'))
  } finally {
    olvidarSesion(queryClient)
  }
}

/** Solo se aceptan rutas internas para volver tras identificarse (evita redirecciones abiertas). */
export function rutaSegura(volver: string | undefined): string {
  if (!volver?.startsWith('/') || volver.startsWith('//') || volver.startsWith('/acceso')) {
    return '/clientes'
  }
  return volver
}
