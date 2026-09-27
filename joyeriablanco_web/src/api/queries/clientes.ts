import { queryOptions, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, unwrap } from '../client'
import type { ClienteEdicionEntrada, ClienteEntrada } from '../tipos'

export const CLIENTES_KEY = ['clientes'] as const

export const clienteQuery = (id: string) =>
  queryOptions({
    queryKey: [...CLIENTES_KEY, 'ficha', id],
    queryFn: () =>
      unwrap(api.GET('/api/v1/clientes/{cliente_id}', { params: { path: { cliente_id: id } } })),
  })

function useInvalidarClientes() {
  const queryClient = useQueryClient()
  return () => queryClient.invalidateQueries({ queryKey: CLIENTES_KEY })
}

export function useCrearCliente() {
  const invalidar = useInvalidarClientes()
  return useMutation({
    mutationFn: (body: ClienteEntrada) => unwrap(api.POST('/api/v1/clientes', { body })),
    onSuccess: invalidar,
  })
}

export function useEditarCliente(id: string) {
  const invalidar = useInvalidarClientes()
  return useMutation({
    mutationFn: (body: ClienteEdicionEntrada) =>
      unwrap(
        api.PUT('/api/v1/clientes/{cliente_id}', { params: { path: { cliente_id: id } }, body }),
      ),
    onSuccess: invalidar,
  })
}
