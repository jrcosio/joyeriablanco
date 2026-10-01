import { TriangleAlert } from 'lucide-react'
import { useState } from 'react'
import type { CausaRectificacion, MotivoModificacion } from '../../api/tipos'
import { Button } from '../../components/ui/Button'
import { Dialog } from '../../components/ui/Dialog'
import { OpcionesRadio } from '../../components/ui/OpcionesRadio'
import { TextField } from '../../components/ui/TextField'
import { CAUSAS_RECTIFICACION, MOTIVOS_MODIFICACION, textoTipoIva } from '../../lib/facturacion'

export interface MotivoElegido {
  motivo: MotivoModificacion
  causa: CausaRectificacion | null
  motivo_texto: string
}

function esMotivo(valor: string): valor is MotivoModificacion {
  return valor in MOTIVOS_MODIFICACION
}

function esCausa(valor: string): valor is CausaRectificacion {
  return valor in CAUSAS_RECTIFICACION
}

/**
 * Motivo de «Modificar» (FR-024): decide la corrección que se genera y lo dice antes de confirmar.
 * En una rectificativa solo cabe «ya entregada»: para reemitirla, se anula y se modifica la
 * original (spec, casos límite).
 */
export function MotivoModificacionDialog({
  isOpen,
  onOpenChange,
  numSerie,
  esRectificativa,
  proximoNumero,
  ivaOriginal,
  ivaVigente,
  enviando,
  onConfirmar,
}: {
  isOpen: boolean
  onOpenChange: (abierto: boolean) => void
  numSerie: string
  esRectificativa: boolean
  /** Número previsto de la factura que sustituye en una reemisión. */
  proximoNumero: string
  /** Tipo de la original y de la corrección; `null` si van sin IVA por oro de inversión. */
  ivaOriginal: string | null
  ivaVigente: string | null
  enviando: boolean
  onConfirmar: (elegido: MotivoElegido) => void
}) {
  const [motivo, setMotivo] = useState<MotivoModificacion | null>(
    esRectificativa ? 'factura_entregada' : null,
  )
  const [causa, setCausa] = useState<CausaRectificacion | null>(null)
  const [texto, setTexto] = useState('')
  const [intentado, setIntentado] = useState(false)

  const faltaCausa = motivo === 'factura_entregada' && causa === null
  const faltaTexto = texto.trim() === ''
  const confirmar = () => {
    setIntentado(true)
    if (motivo === null || faltaCausa || faltaTexto) return
    onConfirmar({
      motivo,
      causa: motivo === 'factura_entregada' ? causa : null,
      motivo_texto: texto.trim(),
    })
  }

  const motivos = (Object.keys(MOTIVOS_MODIFICACION) as MotivoModificacion[])
    .filter((id) => !esRectificativa || id === 'factura_entregada')
    .map((id) => ({ id, label: MOTIVOS_MODIFICACION[id] }))
  const causas = (Object.keys(CAUSAS_RECTIFICACION) as CausaRectificacion[]).map((id) => ({
    id,
    label: CAUSAS_RECTIFICACION[id],
    description: id === 'devolucion_o_precio' ? 'Rectificativa R1' : 'Rectificativa R4',
  }))

  return (
    <Dialog
      title="Motivo de la modificación"
      role="alertdialog"
      isOpen={isOpen}
      onOpenChange={onOpenChange}
    >
      <div className="flex flex-col gap-5">
        <OpcionesRadio
          label="¿Qué ha pasado con la factura?"
          options={motivos}
          value={motivo}
          onChange={(v) => {
            if (esMotivo(v)) setMotivo(v)
          }}
          isRequired
          error={intentado && motivo === null ? 'Elige el motivo.' : undefined}
        />
        {motivo === 'factura_entregada' ? (
          <OpcionesRadio
            label="Causa de la rectificación"
            options={causas}
            value={causa}
            onChange={(v) => {
              if (esCausa(v)) setCausa(v)
            }}
            isRequired
            error={intentado && faltaCausa ? 'Elige la causa.' : undefined}
          />
        ) : null}
        <TextField
          label="Explica el motivo"
          multiline
          isRequired
          maxLength={500}
          value={texto}
          onChange={setTexto}
          error={intentado && faltaTexto ? 'Campo obligatorio.' : undefined}
        />
        {motivo ? (
          <p
            role="status"
            className="border-l border-primary-container pl-4 body-md text-on-surface"
          >
            {motivo === 'no_debio_emitirse'
              ? `Se anulará ${numSerie} y se emitirá una factura nueva con el siguiente número (previsto ${proximoNumero}).`
              : `Se emitirá una factura rectificativa de la serie REC que sustituye a ${numSerie}, que quedará rectificada.`}
          </p>
        ) : null}
        {ivaOriginal !== null && ivaVigente !== null && ivaOriginal !== ivaVigente ? (
          <p className="flex items-start gap-3 border border-warning/40 bg-warning/8 px-4 py-3 body-md text-on-surface">
            <TriangleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-warning" />
            <span>
              {numSerie} tiene un IVA del {textoTipoIva(ivaOriginal)}; la factura nueva se emitirá
              con el {textoTipoIva(ivaVigente)} vigente en Configuración.
            </span>
          </p>
        ) : null}
        <div className="mt-2 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button
            variant="secondary"
            onPress={() => {
              onOpenChange(false)
            }}
          >
            Volver
          </Button>
          <Button onPress={confirmar} isDisabled={enviando}>
            {enviando ? 'Guardando…' : 'Confirmar'}
          </Button>
        </div>
      </div>
    </Dialog>
  )
}
