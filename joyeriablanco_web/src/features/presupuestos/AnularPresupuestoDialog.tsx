import { MotivoPresupuestoDialog } from './MotivoPresupuestoDialog'

/**
 * «Anular» un presupuesto pendiente o caducado (FR-016): solo administradores y con un motivo
 * obligatorio, p. ej. «Rechazado por el cliente». No emite nada ni consume números.
 */
export function AnularPresupuestoDialog({
  isOpen,
  onOpenChange,
  numSerie,
  enviando,
  onConfirmar,
}: {
  isOpen: boolean
  onOpenChange: (abierto: boolean) => void
  numSerie: string
  enviando: boolean
  onConfirmar: (motivoTexto: string) => void
}) {
  return (
    <MotivoPresupuestoDialog
      titulo={`¿Anular el presupuesto ${numSerie}?`}
      etiquetaConfirmar="Anular presupuesto"
      etiquetaEnviando="Anulando…"
      destructivo
      isOpen={isOpen}
      onOpenChange={onOpenChange}
      enviando={enviando}
      onConfirmar={onConfirmar}
    >
      Quedará anulado: ya no se podrá convertir en factura ni modificar. El presupuesto se conserva
      con su motivo en el historial. No se puede deshacer.
    </MotivoPresupuestoDialog>
  )
}
