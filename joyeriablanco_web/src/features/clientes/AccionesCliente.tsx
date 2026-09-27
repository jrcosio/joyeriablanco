import { useState } from 'react'
import { ApiError } from '../../api/client'
import {
  useBorrarCliente,
  useDesactivarCliente,
  useReactivarCliente,
} from '../../api/queries/clientes'
import type { ClienteSalida } from '../../api/tipos'
import { Alerta } from '../../components/forms/Alerta'
import { Button } from '../../components/ui/Button'
import { Dialog } from '../../components/ui/Dialog'
import { TextField } from '../../components/ui/TextField'
import { toast } from '../../components/ui/toast-store'

function normalizar(texto: string): string {
  return texto.replace(/[\s\-./]/g, '').toUpperCase()
}

/**
 * Ciclo de vida del cliente (US4): desactivar con confirmación, reactivar y borrado definitivo
 * solo para administradores, con confirmación reforzada (FR-036, FR-037, FR-058).
 */
export function AccionesCliente({
  cliente,
  esAdmin,
  onBorrado,
}: {
  cliente: ClienteSalida
  esAdmin: boolean
  onBorrado: () => void
}) {
  const desactivar = useDesactivarCliente()
  const reactivar = useReactivarCliente()
  const borrar = useBorrarCliente()
  const [confirmarBaja, setConfirmarBaja] = useState(false)
  const [confirmarBorrado, setConfirmarBorrado] = useState(false)
  const [confirmacion, setConfirmacion] = useState('')
  const [error, setError] = useState<string | null>(null)

  const coincide = normalizar(confirmacion) === cliente.identificacion_numero

  const ejecutar = async (accion: () => Promise<unknown>, mensaje: string) => {
    setError(null)
    try {
      await accion()
      toast(mensaje)
      return true
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se ha podido completar la operación.')
      return false
    }
  }

  return (
    <div className="mt-4 flex flex-col gap-3 border-t border-primary-container/18 pt-5">
      <h3 className="label-md text-primary">Estado del cliente</h3>
      <div className="flex flex-wrap gap-3">
        {cliente.activo ? (
          <Button
            variant="danger"
            onPress={() => {
              setConfirmarBaja(true)
            }}
          >
            Desactivar cliente
          </Button>
        ) : (
          <Button
            variant="secondary"
            isDisabled={reactivar.isPending}
            onPress={() => {
              void ejecutar(() => reactivar.mutateAsync(cliente.id), 'Cliente reactivado.')
            }}
          >
            Reactivar cliente
          </Button>
        )}
        {esAdmin ? (
          <Button
            variant="danger"
            onPress={() => {
              setConfirmacion('')
              setError(null)
              setConfirmarBorrado(true)
            }}
          >
            Borrar definitivamente
          </Button>
        ) : null}
      </div>
      {!confirmarBaja && !confirmarBorrado ? <Alerta mensaje={error} /> : null}

      <Dialog
        title={`¿Desactivar a ${cliente.nombre}?`}
        role="alertdialog"
        isOpen={confirmarBaja}
        onOpenChange={setConfirmarBaja}
      >
        <p className="body-md text-on-surface-variant">
          Dejará de aparecer en el listado por defecto y en los indicadores. Sus datos se conservan
          y podrás reactivarlo cuando quieras.
        </p>
        <Alerta mensaje={error} />
        <div className="mt-2 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button
            variant="secondary"
            onPress={() => {
              setConfirmarBaja(false)
            }}
          >
            Cancelar
          </Button>
          <Button
            isDisabled={desactivar.isPending}
            onPress={() => {
              void ejecutar(() => desactivar.mutateAsync(cliente.id), 'Cliente desactivado.').then(
                (ok) => {
                  if (ok) setConfirmarBaja(false)
                },
              )
            }}
          >
            Desactivar
          </Button>
        </div>
      </Dialog>

      <Dialog
        title="Borrar definitivamente"
        role="alertdialog"
        isOpen={confirmarBorrado}
        onOpenChange={setConfirmarBorrado}
      >
        <p className="body-md text-on-surface-variant">
          Se borrará <strong className="text-on-surface">{cliente.nombre}</strong> de forma
          permanente. Solo es posible si nunca ha tenido facturas ni presupuestos; en otro caso,
          desactívalo. Esta acción no se puede deshacer.
        </p>
        <TextField
          label={`Escribe la identificación (${cliente.identificacion_numero}) para confirmar`}
          value={confirmacion}
          onChange={setConfirmacion}
          autoComplete="off"
        />
        <Alerta mensaje={error} />
        <div className="mt-2 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button
            variant="secondary"
            onPress={() => {
              setConfirmarBorrado(false)
            }}
          >
            Cancelar
          </Button>
          <Button
            variant="danger"
            isDisabled={!coincide || borrar.isPending}
            onPress={() => {
              void ejecutar(() => borrar.mutateAsync(cliente.id), 'Cliente borrado.').then((ok) => {
                if (ok) {
                  setConfirmarBorrado(false)
                  onBorrado()
                }
              })
            }}
          >
            Borrar
          </Button>
        </div>
      </Dialog>
    </div>
  )
}
