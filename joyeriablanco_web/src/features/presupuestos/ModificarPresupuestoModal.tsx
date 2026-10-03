import { zodResolver } from '@hookform/resolvers/zod'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { ApiError } from '../../api/client'
import {
  parametrosPresupuestoQuery,
  presupuestoQuery,
  useModificarPresupuesto,
} from '../../api/queries/presupuestos'
import type { ParametrosPresupuestoSalida, PresupuestoSalida } from '../../api/tipos'
import { Alerta } from '../../components/forms/Alerta'
import { Button } from '../../components/ui/Button'
import { Dialog } from '../../components/ui/Dialog'
import { ModalDocumento } from '../../components/ui/ModalDocumento'
import { toast } from '../../components/ui/toast-store'
import { useClaveOperacion } from '../../lib/idempotencia'
import { CargandoModal } from '../documentos/CargandoModal'
import { etiquetaCliente } from '../documentos/documento-valores'
import { CamposPresupuesto } from './CamposPresupuesto'
import { MotivoPresupuestoDialog } from './MotivoPresupuestoDialog'
import {
  aCuerpo,
  campoDelServidor,
  esquema,
  valoresDelPresupuesto,
  type ValoresPresupuesto,
} from './presupuesto-valores'

const SIN_CONEXION =
  'No se ha podido guardar la modificación. Tus datos siguen aquí: vuelve a intentarlo, sin riesgo de duplicarla.'

/** Se puede modificar un pendiente o un caducado (FR-015). */
const MODIFICABLES: readonly PresupuestoSalida['estado'][] = ['pendiente', 'caducado']

function FormularioModificacion({
  presupuesto,
  parametros,
  onCerrar,
  onModificado,
}: {
  presupuesto: PresupuestoSalida
  parametros: ParametrosPresupuestoSalida
  onCerrar: () => void
  onModificado: (nuevo: PresupuestoSalida) => void
}) {
  const modificar = useModificarPresupuesto()
  const { clave, renovar } = useClaveOperacion()
  const [nombreCliente, setNombreCliente] = useState<string | undefined>(
    etiquetaCliente(presupuesto.cliente),
  )
  const [pidiendoMotivo, setPidiendoMotivo] = useState(false)
  const [descartando, setDescartando] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const form = useForm<ValoresPresupuesto>({
    resolver: zodResolver(esquema),
    defaultValues: valoresDelPresupuesto(presupuesto, parametros.hoy, parametros.validez_dias),
  })
  const sucio = form.formState.isDirty

  const intentarCerrar = () => {
    if (sucio) setDescartando(true)
    else onCerrar()
  }

  const pedirMotivo = form.handleSubmit((valores) => {
    setError(null)
    if (!valores.cliente_id) {
      form.setError('cliente_id', { message: 'Elige el cliente.' })
      return
    }
    if (valores.lineas.length === 0) {
      form.setError('lineas', { message: 'El presupuesto debe tener al menos una línea.' })
      return
    }
    setPidiendoMotivo(true)
  })

  const guardar = async (motivoTexto: string) => {
    setError(null)
    try {
      const nuevo = await modificar.mutateAsync({
        id: presupuesto.id,
        body: { ...aCuerpo(form.getValues()), motivo_texto: motivoTexto },
        clave,
      })
      renovar()
      setPidiendoMotivo(false)
      toast(`Se ha emitido ${nuevo.num_serie}. ${presupuesto.num_serie} queda sustituido`)
      onModificado(nuevo)
    } catch (e) {
      setPidiendoMotivo(false)
      if (!(e instanceof ApiError) || e.tipo === 'red') {
        setError(SIN_CONEXION)
      } else if (e.tipo === 'validacion' && e.problema.errores?.length) {
        for (const [campo, mensaje] of Object.entries(e.porCampo)) {
          const destino = campoDelServidor(campo)
          if (destino) form.setError(destino, { message: mensaje })
          else setError(mensaje)
        }
      } else if (e.tipo === 'cliente-no-facturable') {
        form.setError('cliente_id', { message: e.message })
      } else {
        // `sin-cambios`, `presupuesto-no-modificable`, `emision-no-disponible`…
        setError(e.message)
      }
    }
  }

  return (
    <ModalDocumento
      title={`Modificar presupuesto ${presupuesto.num_serie}`}
      subtitle="Se emitirá un presupuesto nuevo que lo sustituye; el original no cambia."
      isOpen
      onOpenChange={(abierto) => {
        if (!abierto) intentarCerrar()
      }}
      footer={
        <>
          <Button variant="ghost" onPress={intentarCerrar} className="sm:mr-auto">
            Cancelar
          </Button>
          <Button onPress={() => void pedirMotivo()} isDisabled={modificar.isPending}>
            Guardar
          </Button>
        </>
      }
    >
      <CamposPresupuesto
        form={form}
        parametros={parametros}
        numeroAyuda="El presupuesto nuevo recibe el siguiente número."
        nombreCliente={nombreCliente}
        onNombreCliente={setNombreCliente}
        onSubmit={() => void pedirMotivo()}
        despues={<Alerta mensaje={error} />}
      />
      <MotivoPresupuestoDialog
        key={String(pidiendoMotivo)}
        titulo={`¿Sustituir ${presupuesto.num_serie}?`}
        etiquetaConfirmar="Emitir el nuevo"
        etiquetaEnviando="Emitiendo…"
        isOpen={pidiendoMotivo}
        onOpenChange={setPidiendoMotivo}
        enviando={modificar.isPending}
        onConfirmar={(motivo) => void guardar(motivo)}
      >
        Se emitirá un presupuesto nuevo con el siguiente número ({parametros.proximo_numero}) y{' '}
        {presupuesto.num_serie} quedará sustituido por él. Indica el motivo del cambio.
      </MotivoPresupuestoDialog>
      <Dialog
        title="¿Descartar los cambios?"
        role="alertdialog"
        isOpen={descartando}
        onOpenChange={setDescartando}
      >
        <p className="body-md text-on-surface-variant">
          Hay cambios sin guardar en esta modificación. Si cierras, se perderán.
        </p>
        <div className="mt-2 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button
            variant="secondary"
            onPress={() => {
              setDescartando(false)
            }}
          >
            Seguir editando
          </Button>
          <Button
            onPress={() => {
              onCerrar()
            }}
          >
            Descartar
          </Button>
        </div>
      </Dialog>
    </ModalDocumento>
  )
}

/** Modal «Modificar presupuesto» (US4; FR-015): solo administradores, con los datos precargados. */
export function ModificarPresupuestoModal({
  presupuestoId,
  onCerrar,
  onModificado,
}: {
  presupuestoId: string
  onCerrar: () => void
  onModificado: (nuevo: PresupuestoSalida) => void
}) {
  const parametros = useQuery(parametrosPresupuestoQuery)
  const presupuesto = useQuery(presupuestoQuery(presupuestoId))
  if (!parametros.data || !presupuesto.data) {
    const error = presupuesto.isError
      ? presupuesto.error.message
      : parametros.isError
        ? 'No se han podido cargar los datos del presupuesto. Cierra y vuelve a intentarlo.'
        : null
    return <CargandoModal titulo="Modificar presupuesto" error={error} onCerrar={onCerrar} />
  }
  if (!MODIFICABLES.includes(presupuesto.data.estado)) {
    return (
      <ModalDocumento
        title={`Modificar presupuesto ${presupuesto.data.num_serie}`}
        isOpen
        onOpenChange={(abierto) => {
          if (!abierto) onCerrar()
        }}
        footer={
          <Button variant="ghost" onPress={onCerrar}>
            Cerrar
          </Button>
        }
      >
        <p className="body-md text-on-surface">
          Solo se puede modificar un presupuesto pendiente o caducado que no esté en facturación.
          Vuelve a su consulta para ver su estado.
        </p>
      </ModalDocumento>
    )
  }
  return (
    <FormularioModificacion
      presupuesto={presupuesto.data}
      parametros={parametros.data}
      onCerrar={onCerrar}
      onModificado={onModificado}
    />
  )
}
