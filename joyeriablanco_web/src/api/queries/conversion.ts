import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api, unwrap } from '../client'
import { borradorQuery } from './borradores'
import { CLIENTES_KEY } from './clientes'
import { FACTURAS_KEY } from './facturas'
import { PRESUPUESTOS_KEY } from './presupuestos'

/**
 * «Convertir en factura» (005, FR-018; research R-5): crea el borrador de factura vinculado, o
 * devuelve el que ya existe. No lleva clave de operación: la unicidad del borrador vinculado la hace
 * idempotente. Se invalidan presupuestos, facturas y clientes, y el borrador queda en la caché.
 *
 * Vive aparte de `presupuestos.ts` y `borradores.ts` para no crear un ciclo entre los dos.
 */
export function useConvertirPresupuesto() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(
        api.POST('/api/v1/presupuestos/{presupuesto_id}/conversion', {
          params: { path: { presupuesto_id: id } },
        }),
      ),
    onSuccess: async (borrador) => {
      queryClient.setQueryData(borradorQuery(borrador.id).queryKey, borrador)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: PRESUPUESTOS_KEY }),
        queryClient.invalidateQueries({ queryKey: FACTURAS_KEY }),
        queryClient.invalidateQueries({ queryKey: CLIENTES_KEY }),
      ])
    },
  })
}
