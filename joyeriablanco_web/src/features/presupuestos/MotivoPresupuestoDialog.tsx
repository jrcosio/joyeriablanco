import { useState, type ReactNode } from 'react'
import { Button } from '../../components/ui/Button'
import { Dialog } from '../../components/ui/Dialog'
import { TextField } from '../../components/ui/TextField'

/**
 * Pide el motivo, de texto libre y obligatorio, de un cierre del presupuesto (FR-015, FR-016):
 * la sustitución al «Modificar» y la anulación. Se monta de nuevo en cada apertura (`key`), así
 * que el texto empieza vacío.
 */
export function MotivoPresupuestoDialog({
  titulo,
  children,
  etiquetaConfirmar,
  etiquetaEnviando,
  destructivo = false,
  isOpen,
  onOpenChange,
  enviando,
  onConfirmar,
}: {
  titulo: string
  children: ReactNode
  etiquetaConfirmar: string
  etiquetaEnviando: string
  destructivo?: boolean
  isOpen: boolean
  onOpenChange: (abierto: boolean) => void
  enviando: boolean
  onConfirmar: (motivoTexto: string) => void
}) {
  const [texto, setTexto] = useState('')
  const [intentado, setIntentado] = useState(false)
  const faltaTexto = texto.trim() === ''

  const confirmar = () => {
    setIntentado(true)
    if (faltaTexto) return
    onConfirmar(texto.trim())
  }

  return (
    <Dialog title={titulo} role="alertdialog" isOpen={isOpen} onOpenChange={onOpenChange}>
      <div className="flex flex-col gap-5">
        <div className="body-md text-on-surface-variant">{children}</div>
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
          <Button
            variant={destructivo ? 'danger' : 'primary'}
            onPress={confirmar}
            isDisabled={enviando}
          >
            {enviando ? etiquetaEnviando : etiquetaConfirmar}
          </Button>
        </div>
      </div>
    </Dialog>
  )
}
