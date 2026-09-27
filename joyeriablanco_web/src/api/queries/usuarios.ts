import { queryOptions, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, unwrap } from '../client'
import type { Rol, UsuarioAltaEntrada } from '../tipos'

export const USUARIOS_KEY = ['usuarios'] as const

export const usuariosQuery = queryOptions({
  queryKey: USUARIOS_KEY,
  queryFn: () => unwrap(api.GET('/api/v1/usuarios')),
})

/** Incluye a los eliminados, marcados con `eliminado`: filtro de la auditoría (FR-061). */
export const usuariosConEliminadosQuery = queryOptions({
  queryKey: [...USUARIOS_KEY, 'con-eliminados'],
  queryFn: () =>
    unwrap(api.GET('/api/v1/usuarios', { params: { query: { incluir_eliminados: true } } })),
})

function useMutacionUsuarios<V, R>(fn: (variables: V) => Promise<R>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: USUARIOS_KEY }),
  })
}

const ruta = (id: string) => ({ params: { path: { usuario_id: id } } })

export const useCrearUsuario = () =>
  useMutacionUsuarios((body: UsuarioAltaEntrada) => unwrap(api.POST('/api/v1/usuarios', { body })))

export const useCambiarRol = () =>
  useMutacionUsuarios(({ id, rol }: { id: string; rol: Rol }) =>
    unwrap(api.PATCH('/api/v1/usuarios/{usuario_id}', { ...ruta(id), body: { rol } })),
  )

export const useDesactivarUsuario = () =>
  useMutacionUsuarios((id: string) =>
    unwrap(api.POST('/api/v1/usuarios/{usuario_id}/desactivacion', ruta(id))),
  )

export const useReactivarUsuario = () =>
  useMutacionUsuarios((id: string) =>
    unwrap(api.POST('/api/v1/usuarios/{usuario_id}/reactivacion', ruta(id))),
  )

export const useEliminarUsuario = () =>
  useMutacionUsuarios((id: string) => unwrap(api.DELETE('/api/v1/usuarios/{usuario_id}', ruta(id))))

export const useRestablecerContrasena = () =>
  useMutacionUsuarios((id: string) =>
    unwrap(api.POST('/api/v1/usuarios/{usuario_id}/restablecimiento-contrasena', ruta(id))),
  )
