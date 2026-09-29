import { useState } from 'react'
import { Button } from '../../components/ui/Button'
import { Casilla } from '../../components/ui/Casilla'
import { Dialog } from '../../components/ui/Dialog'
import { TextField } from '../../components/ui/TextField'

/**
 * Anular sin reemitir (FR-025): declaración obligatoria y motivo. Si es una rectificativa, avisa
 * de que la factura que rectificaba vuelve a estar vigente (FR-048).
 */
export function AnularFacturaDialog({
  isOpen,
  onOpenChange,
  numSerie,
  reactivara,
  enviando,
  onConfirmar,
}: {
  isOpen: boolean
  onOpenChange: (abierto: boolean) => void
  numSerie: string
  /** Número de la factura que volverá a estar vigente, si se anula una rectificativa. */
  reactivara: string | undefined
  enviando: boolean
  onConfirmar: (motivoTexto: string) => void
}) {
  const [declarada, setDeclarada] = useState(false)
  const [texto, setTexto] = useState('')
  const [intentado, setIntentado] = useState(false)
  const faltaTexto = texto.trim() === ''

  const confirmar = () => {
    setIntentado(true)
    if (!declarada || faltaTexto) return
    onConfirmar(texto.trim())
  }

  return (
    <Dialog
      title={`¿Anular la factura ${numSerie}?`}
      role="alertdialog"
      isOpen={isOpen}
      onOpenChange={onOpenChange}
    >
      <div className="flex flex-col gap-5">
        <p className="body-md text-on-surface-variant">
          Se generará su registro de anulación y quedará sin efecto, sin factura que la sustituya.
          Solo procede si la factura no debió emitirse (por ejemplo, un duplicado). No se puede
          deshacer.
        </p>
        {reactivara ? (
          <p
            role="status"
            className="border-l-2 border-primary-container pl-4 body-md text-on-surface"
          >
            {reactivara} volverá a estar vigente.
          </p>
        ) : null}
        <div className="flex flex-col gap-1.5">
          <Casilla
            isSelected={declarada}
            onChange={setDeclarada}
            isRequired
            isInvalid={intentado && !declarada}
          >
            Declaro que esta factura no debió emitirse
          </Casilla>
          {intentado && !declarada ? (
            <p className="body-sm text-danger">Hace falta la declaración para anular.</p>
          ) : null}
        </div>
        <TextField
          label="Motivo"
          multiline
          isRequired
          maxLength={500}
          value={texto}
          onChange={setTexto}
          error={intentado && faltaTexto ? 'Campo obligatorio.' : undefined}
        />
        <div className="mt-2 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button
            variant="secondary"
            onPress={() => {
              onOpenChange(false)
            }}
          >
            Volver
          </Button>
          <Button variant="danger" onPress={confirmar} isDisabled={enviando}>
            {enviando ? 'Anulando…' : 'Anular factura'}
          </Button>
        </div>
      </div>
    </Dialog>
  )
}
