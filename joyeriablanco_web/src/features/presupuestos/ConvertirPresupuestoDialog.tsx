import { useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import { ApiError, type Problema } from '../../api/client'
import { useConvertirPresupuesto } from '../../api/queries/conversion'
import type { PresupuestoSalida } from '../../api/tipos'
import { Alerta } from '../../components/forms/Alerta'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { toast } from '../../components/ui/toast-store'
import { fechaCorta } from '../../lib/fechas'

const SIN_CONEXION =
  'No se ha podido conectar con el servidor. Vuelve a intentarlo: si el borrador llegó a crearse, se abrirá el mismo.'

/**
 * «Convertir en factura» (005, FR-018; contracts/ui-rutas.md). Confirma, crea el borrador de
 * factura vinculado (o recibe el que ya existía) y lo abre. Si el presupuesto ya no se puede
 * convertir, la consulta lo explica y se recarga (`onNoModificable`).
 */
export function ConvertirPresupuestoDialog({
  presupuesto,
  isOpen,
  onOpenChange,
  onNoModificable,
}: {
  presupuesto: Pick<PresupuestoSalida, 'id' | 'num_serie' | 'estado' | 'valido_hasta'>
  isOpen: boolean
  onOpenChange: (abierto: boolean) => void
  onNoModificable: (problema: Problema) => void
}) {
  const convertir = useConvertirPresupuesto()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)

  const confirmar = async () => {
    setError(null)
    try {
      const borrador = await convertir.mutateAsync(presupuesto.id)
      onOpenChange(false)
      toast(`Borrador de factura creado a partir de ${presupuesto.num_serie}`)
      await navigate({
        to: '/facturas/borradores/$borradorId',
        params: { borradorId: borrador.id },
      })
    } catch (e) {
      if (e instanceof ApiError && e.tipo === 'presupuesto-no-modificable') {
        onOpenChange(false)
        onNoModificable(e.problema)
      } else {
        setError(e instanceof ApiError && e.tipo !== 'red' ? e.message : SIN_CONEXION)
      }
    }
  }

  return (
    <ConfirmDialog
      title="¿Convertir en factura?"
      isOpen={isOpen}
      onOpenChange={(abierto) => {
        if (!abierto) setError(null)
        onOpenChange(abierto)
      }}
      onConfirm={() => void confirmar()}
      confirmLabel={convertir.isPending ? 'Creando…' : 'Convertir en factura'}
      isPending={convertir.isPending}
    >
      <div className="flex flex-col gap-3">
        <p>
          Se creará un borrador de factura con los datos de {presupuesto.num_serie}. Podrás
          revisarlo antes de emitirlo.
        </p>
        {presupuesto.estado === 'caducado' ? (
          <p className="text-on-surface">
            La validez de este presupuesto venció el {fechaCorta(presupuesto.valido_hasta)}.
          </p>
        ) : null}
        <Alerta mensaje={error} />
      </div>
    </ConfirmDialog>
  )
}
