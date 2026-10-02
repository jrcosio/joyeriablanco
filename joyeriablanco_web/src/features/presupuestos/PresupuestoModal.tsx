import { zodResolver } from '@hookform/resolvers/zod'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { useState } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { ApiError } from '../../api/client'
import {
  borradorPresupuestoQuery,
  useCrearBorradorPresupuesto,
  useEliminarBorradorPresupuesto,
  useEmitirBorradorPresupuesto,
  useGuardarBorradorPresupuesto,
} from '../../api/queries/borradoresPresupuesto'
import { parametrosPresupuestoQuery, useEmitirPresupuesto } from '../../api/queries/presupuestos'
import type {
  BorradorPresupuestoSalida,
  ParametrosPresupuestoSalida,
  PresupuestoSalida,
} from '../../api/tipos'
import { useSesion } from '../../auth/session'
import { Alerta } from '../../components/forms/Alerta'
import { Button } from '../../components/ui/Button'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { Dialog } from '../../components/ui/Dialog'
import { ModalDocumento } from '../../components/ui/ModalDocumento'
import { toast } from '../../components/ui/toast-store'
import { textoFalta } from '../../lib/facturacion'
import { useClaveOperacion } from '../../lib/idempotencia'
import { AvisoCambioIva } from '../documentos/AvisoCambioIva'
import { CargandoModal } from '../documentos/CargandoModal'
import { etiquetaCliente } from '../documentos/documento-valores'
import { CamposPresupuesto } from './CamposPresupuesto'
import {
  aCuerpo,
  aCuerpoBorrador,
  campoDelServidor,
  erroresParaEmitir,
  esquema,
  valoresDelBorrador,
  valoresIniciales,
  type ValoresPresupuesto,
} from './presupuesto-valores'

const YA_NO_EXISTE =
  'Este borrador ya se ha emitido o se ha eliminado. Ciérralo y búscalo en el listado.'

function AvisoNoEmitible({ faltan }: { faltan: readonly string[] }) {
  const { usuario } = useSesion()
  return (
    <p className="body-sm text-on-surface-variant">
      No se puede emitir todavía: falta {faltan.map(textoFalta).join(', ')}.{' '}
      {usuario.rol === 'administrador' ? (
        <Link to="/configuracion/facturacion" className="text-primary underline underline-offset-4">
          Completar la configuración
        </Link>
      ) : (
        'Un administrador debe completarlo en Configuración.'
      )}
    </p>
  )
}

/** Confirmación previa a emitir (FR-014): un presupuesto emitido ya no se edita. */
export function ConfirmarEmisionPresupuestoDialog({
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
      title="¿Emitir el presupuesto?"
      role="alertdialog"
      isOpen={isOpen}
      onOpenChange={onOpenChange}
    >
      <p className="body-md text-on-surface-variant">
        Al emitirlo recibe su número definitivo. Después ya no se podrá editar: los cambios
        posteriores se harán con «Modificar», que emite uno nuevo y conserva este.
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
          {emitiendo ? 'Emitiendo…' : 'Emitir presupuesto'}
        </Button>
      </div>
    </Dialog>
  )
}

interface FormularioProps {
  parametros: ParametrosPresupuestoSalida
  /** Sin borrador: presupuesto nuevo. Con él: modo borrador (FR-027). */
  borrador?: BorradorPresupuestoSalida | undefined
  onCerrar: () => void
  onEmitido: (presupuesto: PresupuestoSalida) => void
  /** Tras «Guardar borrador» en un presupuesto nuevo, el modal pasa al modo borrador. */
  onBorradorCreado: (borrador: BorradorPresupuestoSalida) => void
}

/**
 * Ciclo del borrador de presupuesto (FR-012 a FR-014), copiado del de la factura (research R-13):
 * crear, guardar con versión, conflicto, descartar, eliminar y emitir con confirmación.
 */
function FormularioPresupuesto({
  parametros,
  borrador,
  onCerrar,
  onEmitido,
  onBorradorCreado,
}: FormularioProps) {
  const queryClient = useQueryClient()
  const emitirNuevo = useEmitirPresupuesto()
  const emitirBorrador = useEmitirBorradorPresupuesto()
  const crearBorrador = useCrearBorradorPresupuesto()
  const guardarBorrador = useGuardarBorradorPresupuesto()
  const eliminarBorrador = useEliminarBorradorPresupuesto()
  const { clave, renovar } = useClaveOperacion()
  const [version, setVersion] = useState(borrador?.version ?? 0)
  const [tipoIvaPrevisto, setTipoIvaPrevisto] = useState(borrador?.tipo_iva_previsto)
  const [error, setError] = useState<string | null>(null)
  const [confirmando, setConfirmando] = useState(false)
  const [descartando, setDescartando] = useState(false)
  const [eliminando, setEliminando] = useState(false)
  const [conflicto, setConflicto] = useState(false)
  const [nombreCliente, setNombreCliente] = useState<string | undefined>(
    borrador?.cliente ? etiquetaCliente(borrador.cliente) : undefined,
  )
  const form = useForm<ValoresPresupuesto>({
    resolver: zodResolver(esquema),
    defaultValues: borrador
      ? valoresDelBorrador(borrador)
      : valoresIniciales(parametros.hoy, parametros.validez_dias),
  })
  const { formState, setError: marcar } = form
  const oroInversion = useWatch({ control: form.control, name: 'oro_inversion' })
  const sucio = formState.isDirty
  const ocupado =
    emitirNuevo.isPending ||
    emitirBorrador.isPending ||
    crearBorrador.isPending ||
    guardarBorrador.isPending ||
    eliminarBorrador.isPending

  const intentarCerrar = () => {
    if (sucio) setDescartando(true)
    else onCerrar()
  }

  const recargar = async () => {
    if (!borrador) return
    await queryClient.invalidateQueries({
      queryKey: borradorPresupuestoQuery(borrador.id).queryKey,
    })
    const actual = await queryClient.query(borradorPresupuestoQuery(borrador.id))
    form.reset(valoresDelBorrador(actual))
    setVersion(actual.version)
    setTipoIvaPrevisto(actual.tipo_iva_previsto)
    setNombreCliente(actual.cliente ? etiquetaCliente(actual.cliente) : undefined)
    setConflicto(false)
    setError(null)
  }

  const mostrarError = (e: unknown, operacion: 'emitir' | 'guardar' | 'eliminar') => {
    if (!(e instanceof ApiError) || e.tipo === 'red') {
      setError(
        operacion === 'emitir'
          ? 'No se ha podido completar la emisión. Tus datos siguen aquí: vuelve a intentarlo, sin riesgo de duplicar el presupuesto.'
          : 'No se ha podido conectar con el servidor. Tus datos siguen aquí: vuelve a intentarlo.',
      )
      return
    }
    if (e.tipo === 'conflicto-version') {
      setConflicto(true)
    } else if (e.tipo === 'no-encontrado' && borrador) {
      setError(YA_NO_EXISTE)
    } else if (e.tipo === 'validacion' && e.problema.errores?.length) {
      for (const [campo, mensaje] of Object.entries(e.porCampo)) {
        const destino = campoDelServidor(campo)
        if (destino) marcar(destino, { message: mensaje })
        else setError(mensaje)
      }
    } else if (e.tipo === 'cliente-no-facturable') {
      marcar('cliente_id', { message: e.message })
    } else {
      setError(e.message)
    }
  }

  const pedirEmision = form.handleSubmit((valores) => {
    setError(null)
    const pendientes = erroresParaEmitir(valores)
    for (const { campo, mensaje } of pendientes) marcar(campo, { message: mensaje })
    if (pendientes.length === 0) setConfirmando(true)
  })

  const confirmarEmision = async () => {
    setError(null)
    const valores = form.getValues()
    try {
      const presupuesto = borrador
        ? await emitirBorrador.mutateAsync({
            id: borrador.id,
            body: { ...aCuerpoBorrador(valores), version },
            clave,
          })
        : await emitirNuevo.mutateAsync({ body: aCuerpo(valores), clave })
      renovar()
      setConfirmando(false)
      toast(`Presupuesto ${presupuesto.num_serie} emitido`)
      onEmitido(presupuesto)
    } catch (e) {
      setConfirmando(false)
      mostrarError(e, 'emitir')
    }
  }

  const guardar = form.handleSubmit(async (valores) => {
    setError(null)
    try {
      if (!borrador) {
        const creado = await crearBorrador.mutateAsync(aCuerpoBorrador(valores))
        toast('Borrador guardado')
        onBorradorCreado(creado)
        return
      }
      const guardado = await guardarBorrador.mutateAsync({
        id: borrador.id,
        body: { ...aCuerpoBorrador(valores), version },
      })
      form.reset(valoresDelBorrador(guardado))
      setVersion(guardado.version)
      setTipoIvaPrevisto(guardado.tipo_iva_previsto)
      toast('Borrador guardado')
    } catch (e) {
      mostrarError(e, 'guardar')
    }
  })

  const eliminar = async () => {
    if (!borrador) return
    setError(null)
    try {
      await eliminarBorrador.mutateAsync(borrador.id)
      setEliminando(false)
      toast('Borrador eliminado')
      onCerrar()
    } catch (e) {
      setEliminando(false)
      mostrarError(e, 'eliminar')
    }
  }

  return (
    <ModalDocumento
      title={borrador ? 'Borrador de presupuesto' : 'Nuevo presupuesto'}
      isOpen
      onOpenChange={(abierto) => {
        if (!abierto) intentarCerrar()
      }}
      footer={
        <>
          <Button variant="ghost" onPress={intentarCerrar} className="sm:mr-auto">
            Cancelar
          </Button>
          {parametros.emision_posible ? null : <AvisoNoEmitible faltan={parametros.faltan} />}
          {borrador ? (
            <Button
              variant="danger"
              onPress={() => {
                setEliminando(true)
              }}
              isDisabled={ocupado}
            >
              Eliminar borrador
            </Button>
          ) : null}
          <Button variant="secondary" onPress={() => void guardar()} isDisabled={ocupado}>
            {crearBorrador.isPending || guardarBorrador.isPending
              ? 'Guardando…'
              : 'Guardar borrador'}
          </Button>
          <Button
            onPress={() => void pedirEmision()}
            isDisabled={!parametros.emision_posible || ocupado}
          >
            Emitir presupuesto
          </Button>
        </>
      }
    >
      <CamposPresupuesto
        form={form}
        parametros={parametros}
        numeroAyuda={
          <>
            Previsto: <span className="tabular-nums">{parametros.proximo_numero}</span>
          </>
        }
        nombreCliente={nombreCliente}
        onNombreCliente={setNombreCliente}
        onSubmit={() => void pedirEmision()}
        antes={
          !oroInversion && tipoIvaPrevisto && tipoIvaPrevisto !== parametros.iva_por_defecto ? (
            <AvisoCambioIva previsto={tipoIvaPrevisto} vigente={parametros.iva_por_defecto} />
          ) : null
        }
        despues={<Alerta mensaje={error} />}
      />
      <ConfirmarEmisionPresupuestoDialog
        isOpen={confirmando}
        onOpenChange={setConfirmando}
        onConfirmar={() => void confirmarEmision()}
        emitiendo={emitirNuevo.isPending || emitirBorrador.isPending}
      />
      <ConfirmDialog
        title="¿Eliminar el borrador?"
        isOpen={eliminando}
        onOpenChange={setEliminando}
        onConfirm={() => void eliminar()}
        confirmLabel="Eliminar borrador"
        destructive
        isPending={eliminarBorrador.isPending}
      >
        Se borrará definitivamente. Como aún no está emitido, no consume ningún número.
      </ConfirmDialog>
      <Dialog
        title="El borrador ha cambiado"
        role="alertdialog"
        isOpen={conflicto}
        onOpenChange={setConflicto}
      >
        <p className="body-md text-on-surface-variant">
          Otra persona ha guardado este borrador desde que lo abriste. Puedes recargar sus datos
          actuales (se descartarán tus cambios) o seguir con el formulario para copiar lo que
          necesites.
        </p>
        <div className="mt-2 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button
            variant="secondary"
            onPress={() => {
              setConflicto(false)
            }}
          >
            Seguir editando
          </Button>
          <Button onPress={() => void recargar()}>Recargar datos</Button>
        </div>
      </Dialog>
      <Dialog
        title="¿Descartar los cambios?"
        role="alertdialog"
        isOpen={descartando}
        onOpenChange={setDescartando}
      >
        <p className="body-md text-on-surface-variant">
          Hay cambios sin guardar en este presupuesto. Si cierras, se perderán.
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

const SIN_PARAMETROS =
  'No se han podido cargar los datos del presupuesto. Cierra y vuelve a intentarlo.'

/** Modal «Nuevo presupuesto» sobre el listado (US1; FR-026, FR-027). */
export function NuevoPresupuestoModal({
  onCerrar,
  onEmitido,
  onBorradorCreado,
}: {
  onCerrar: () => void
  onEmitido: (presupuesto: PresupuestoSalida) => void
  onBorradorCreado: (borrador: BorradorPresupuestoSalida) => void
}) {
  const parametros = useQuery(parametrosPresupuestoQuery)
  if (!parametros.data) {
    return (
      <CargandoModal
        titulo="Nuevo presupuesto"
        error={parametros.isError ? SIN_PARAMETROS : null}
        onCerrar={onCerrar}
      />
    )
  }
  return (
    <FormularioPresupuesto
      parametros={parametros.data}
      onCerrar={onCerrar}
      onEmitido={onEmitido}
      onBorradorCreado={onBorradorCreado}
    />
  )
}

/** Modal «Borrador de presupuesto»: el mismo formulario con «Eliminar borrador» (FR-012). */
export function BorradorPresupuestoModal({
  borradorId,
  onCerrar,
  onEmitido,
}: {
  borradorId: string
  onCerrar: () => void
  onEmitido: (presupuesto: PresupuestoSalida) => void
}) {
  const parametros = useQuery(parametrosPresupuestoQuery)
  const borrador = useQuery(borradorPresupuestoQuery(borradorId))
  if (!parametros.data || !borrador.data) {
    const error = borrador.isError
      ? borrador.error instanceof ApiError && borrador.error.tipo === 'no-encontrado'
        ? YA_NO_EXISTE
        : borrador.error.message
      : parametros.isError
        ? SIN_PARAMETROS
        : null
    return <CargandoModal titulo="Borrador de presupuesto" error={error} onCerrar={onCerrar} />
  }
  return (
    <FormularioPresupuesto
      key={borrador.data.id}
      parametros={parametros.data}
      borrador={borrador.data}
      onCerrar={onCerrar}
      onEmitido={onEmitido}
      onBorradorCreado={() => undefined}
    />
  )
}
