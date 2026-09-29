import { Button } from '../../components/ui/Button'
import { Dialog } from '../../components/ui/Dialog'

/** Confirmación previa a emitir (FR-021): una factura emitida ya no se edita. */
export function ConfirmarEmisionDialog({
  isOpen,
  onOpenChange,
  onConfirmar,
  emitiendo,
}: {
  isOpen: boolean
  onOpenChange: (abierto: boolean) => void
  onConfirmar: () => void
  emitiendo: boolean
}) {
  return (
    <Dialog
      title="¿Emitir la factura?"
      role="alertdialog"
      isOpen={isOpen}
      onOpenChange={onOpenChange}
    >
      <p className="body-md text-on-surface-variant">
        Al emitirla recibe su número definitivo y queda registrada. Después ya no se podrá editar:
        cualquier cambio se hará mediante una corrección (anulación o factura rectificativa), que
        conserva la original.
      </p>
      <div className="mt-2 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
        <Button
          variant="secondary"
          onPress={() => {
            onOpenChange(false)
          }}
        >
          Volver
        </Button>
        <Button onPress={onConfirmar} isDisabled={emitiendo}>
          {emitiendo ? 'Emitiendo…' : 'Emitir factura'}
        </Button>
      </div>
    </Dialog>
  )
}
