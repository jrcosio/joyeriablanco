import { useState } from 'react'
import { Form } from 'react-aria-components'
import { ApiError } from '../../api/client'
import { useAjustarContador } from '../../api/queries/configuracionFacturacion'
import type { AjusteContadorSalida } from '../../api/tipos'
import { Alerta } from '../../components/forms/Alerta'
import { Button } from '../../components/ui/Button'
import { Dialog } from '../../components/ui/Dialog'
import { TextField } from '../../components/ui/TextField'
import { toast } from '../../components/ui/toast-store'

function numeroFactura(anio: number, numero: number): string {
  return `FAC-${anio.toString()}-${numero.toString().padStart(4, '0')}`
}

/**
 * Ajuste al alza del próximo número de la serie ordinaria del año (FR-010; constitución 2.2.0).
 * Primero simula en el servidor para avisar de cuántos números quedarán sin usar y, solo tras
 * confirmar, lo aplica con su motivo, que queda en la auditoría.
 */
export function AjusteContadorDialog({
  isOpen,
  onOpenChange,
}: {
  isOpen: boolean
  onOpenChange: (abierto: boolean) => void
}) {
  const ajustar = useAjustarContador()
  const [proximo, setProximo] = useState('')
  const [motivo, setMotivo] = useState('')
  const [simulacion, setSimulacion] = useState<AjusteContadorSalida | null>(null)
  const [error, setError] = useState<string | null>(null)

  const cerrar = () => {
    setProximo('')
    setMotivo('')
    setSimulacion(null)
    setError(null)
    onOpenChange(false)
  }

  const numero = /^\d+$/.test(proximo.trim()) ? Number.parseInt(proximo.trim(), 10) : null
  const errorNumero = proximo !== '' && numero === null ? 'Escribe un número entero.' : undefined

  const enviar = async (simular: boolean) => {
    if (numero === null || motivo.trim() === '') return
    setError(null)
    try {
      const resultado = await ajustar.mutateAsync({ proximo_numero: numero, motivo, simular })
      if (simular) {
        setSimulacion(resultado)
      } else {
        toast(`La próxima factura será ${numeroFactura(resultado.anio, resultado.proximo_numero)}`)
        cerrar()
      }
    } catch (e) {
      setSimulacion(null)
      setError(e instanceof ApiError ? e.message : 'No se ha podido ajustar la numeración.')
    }
  }

  return (
    <Dialog
      title="Ajustar la numeración"
      isOpen={isOpen}
      onOpenChange={(abierto) => {
        if (!abierto) cerrar()
      }}
    >
      <Form
        className="flex flex-col gap-5"
        validationBehavior="aria"
        onSubmit={(e) => {
          e.preventDefault()
          void enviar(simulacion === null)
        }}
      >
        <p className="body-md text-on-surface-variant">
          Solo se puede subir, nunca bajar ni reutilizar un número. Los números que se salten no se
          asignarán a ninguna factura, así que deben poder justificarse (por ejemplo, porque se
          emitieron con otro programa).
        </p>
        <TextField
          label="Próximo número"
          isRequired
          inputMode="numeric"
          autoFocus
          value={proximo}
          onChange={(v) => {
            setProximo(v)
            setSimulacion(null)
          }}
          error={errorNumero}
        />
        <TextField
          label="Motivo"
          isRequired
          multiline
          description="Queda en la auditoría junto con el ajuste."
          value={motivo}
          onChange={(v) => {
            setMotivo(v)
            setSimulacion(null)
          }}
        />
        <Alerta mensaje={error} />
        {simulacion ? (
          <div role="status" className="border border-warning/40 bg-warning/8 px-4 py-3 body-md">
            {simulacion.numeros_sin_usar === 1
              ? 'Quedará 1 número sin usar'
              : `Quedarán ${simulacion.numeros_sin_usar.toString()} números sin usar`}{' '}
            (del {simulacion.ultimo_usado + 1} al {simulacion.proximo_numero - 1}). La próxima
            factura será {numeroFactura(simulacion.anio, simulacion.proximo_numero)}.
          </div>
        ) : null}
        <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button variant="secondary" onPress={cerrar}>
            Cancelar
          </Button>
          <Button
            type="submit"
            isDisabled={numero === null || motivo.trim() === '' || ajustar.isPending}
          >
            {simulacion ? 'Confirmar ajuste' : 'Continuar'}
          </Button>
        </div>
      </Form>
    </Dialog>
  )
}
