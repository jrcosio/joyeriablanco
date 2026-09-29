import { queryOptions, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, unwrap } from '../client'
import type { AjusteContadorEntrada, ConfiguracionFacturacionEntrada } from '../tipos'

export const CONFIGURACION_FACTURACION_KEY = ['configuracion-facturacion'] as const
export const PARAMETROS_FACTURACION_KEY = ['facturas', 'parametros'] as const

/** Configuración completa: solo administradores (FR-001). */
export const configuracionFacturacionQuery = queryOptions({
  queryKey: CONFIGURACION_FACTURACION_KEY,
  queryFn: () => unwrap(api.GET('/api/v1/configuracion/facturacion')),
})

/** Lo que necesita el modal de factura: IVA vigente, si se puede emitir y el próximo número. */
export const parametrosFacturacionQuery = queryOptions({
  queryKey: PARAMETROS_FACTURACION_KEY,
  queryFn: () => unwrap(api.GET('/api/v1/facturas/parametros')),
})

function useInvalidarConfiguracion() {
  const queryClient = useQueryClient()
  return async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: CONFIGURACION_FACTURACION_KEY }),
      queryClient.invalidateQueries({ queryKey: PARAMETROS_FACTURACION_KEY }),
    ])
  }
}

export function useGuardarConfiguracionFacturacion() {
  const invalidar = useInvalidarConfiguracion()
  return useMutation({
    mutationFn: (body: ConfiguracionFacturacionEntrada) =>
      unwrap(api.PUT('/api/v1/configuracion/facturacion', { body })),
    onSuccess: invalidar,
  })
}

export function useAjustarContador() {
  const invalidar = useInvalidarConfiguracion()
  return useMutation({
    mutationFn: (body: AjusteContadorEntrada) =>
      unwrap(api.POST('/api/v1/configuracion/facturacion/contador', { body })),
    onSuccess: async (resultado) => {
      if (resultado.aplicado) await invalidar()
    },
  })
}
