import { Copy } from 'lucide-react'
import { useState } from 'react'
import { Button } from '../../components/ui/Button'
import { Dialog } from '../../components/ui/Dialog'

/**
 * Muestra la contraseña temporal UNA sola vez (FR-015). Solo se cierra con la confirmación
 * explícita de haberla anotado.
 */
export function ContrasenaTemporalDialog({
  datos,
  onCerrar,
}: {
  datos: { nombreUsuario: string; contrasena: string } | null
  onCerrar: () => void
}) {
  const [copiada, setCopiada] = useState(false)
  return (
    <Dialog
      title="Contraseña temporal"
      role="alertdialog"
      isOpen={datos !== null}
      isDismissable={false}
      onOpenChange={() => undefined}
    >
      {datos ? (
        <>
          <p className="body-md text-on-surface-variant">
            Entrega esta contraseña en persona a{' '}
            <strong className="text-on-surface">{datos.nombreUsuario}</strong>. Caduca en 72 horas y
            tendrá que cambiarla en su primer acceso.
          </p>
          <div className="flex items-center justify-between gap-3 border border-primary-container bg-surface-container-lowest px-4 py-3">
            <code
              aria-label="Contraseña temporal"
              className="title-lg tracking-widest text-primary tabular-nums"
            >
              {datos.contrasena}
            </code>
            <Button
              variant="icon"
              aria-label="Copiar contraseña"
              onPress={() => {
                void navigator.clipboard.writeText(datos.contrasena).then(() => {
                  setCopiada(true)
                })
              }}
            >
              <Copy aria-hidden="true" className="size-4" />
            </Button>
          </div>
          <p role="status" className="body-sm text-warning">
            {copiada ? 'Copiada al portapapeles. ' : ''}No volverá a mostrarse.
          </p>
          <div className="mt-2 flex justify-end">
            <Button
              onPress={() => {
                setCopiada(false)
                onCerrar()
              }}
            >
              He anotado la contraseña
            </Button>
          </div>
        </>
      ) : null}
    </Dialog>
  )
}
