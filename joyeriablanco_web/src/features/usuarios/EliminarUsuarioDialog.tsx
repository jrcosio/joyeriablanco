import { useState } from 'react'
import { ApiError } from '../../api/client'
import { useEliminarUsuario } from '../../api/queries/usuarios'
import type { UsuarioSalida } from '../../api/tipos'
import { Alerta } from '../../components/forms/Alerta'
import { Button } from '../../components/ui/Button'
import { Dialog } from '../../components/ui/Dialog'
import { TextField } from '../../components/ui/TextField'
import { toast } from '../../components/ui/toast-store'

/**
 * Eliminación de un usuario desactivado con confirmación reforzada: hay que escribir su nombre de
 * usuario (FR-058, FR-061). Lo que registró se conserva.
 */
export function EliminarUsuarioDialog({
  usuario,
  onCerrar,
}: {
  usuario: UsuarioSalida | null
  onCerrar: () => void
}) {
  const eliminar = useEliminarUsuario()
  const [confirmacion, setConfirmacion] = useState('')
  const [error, setError] = useState<string | null>(null)

  const cerrar = () => {
    setConfirmacion('')
    setError(null)
    onCerrar()
  }
  const coincide = usuario !== null && confirmacion.trim().toLowerCase() === usuario.nombre_usuario

  const confirmar = async () => {
    if (!usuario) return
    setError(null)
    try {
      await eliminar.mutateAsync(usuario.id)
      toast(`${usuario.nombre} eliminado.`)
      cerrar()
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se ha podido eliminar el usuario.')
    }
  }

  return (
    <Dialog
      title="Eliminar usuario"
      role="alertdialog"
      isOpen={usuario !== null}
      onOpenChange={(abierto) => {
        if (!abierto) cerrar()
      }}
    >
      {usuario ? (
        <>
          <p className="body-md text-on-surface-variant">
            <strong className="text-on-surface">{usuario.nombre}</strong> desaparecerá de la lista
            de usuarios y no podrá volver a entrar. Los clientes, documentos y eventos de auditoría
            que registró se conservan y seguirán mostrando su nombre. Su nombre de usuario quedará
            libre. Esta acción no se puede deshacer.
          </p>
          <TextField
            label={`Escribe el nombre de usuario (${usuario.nombre_usuario}) para confirmar`}
            value={confirmacion}
            onChange={setConfirmacion}
            autoComplete="off"
          />
          <Alerta mensaje={error} />
          <div className="mt-2 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
            <Button variant="secondary" onPress={cerrar}>
              Cancelar
            </Button>
            <Button
              variant="danger"
              isDisabled={!coincide || eliminar.isPending}
              onPress={() => {
                void confirmar()
              }}
            >
              Eliminar
            </Button>
          </div>
        </>
      ) : null}
    </Dialog>
  )
}
