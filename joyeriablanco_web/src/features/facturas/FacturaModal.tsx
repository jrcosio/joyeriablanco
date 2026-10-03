import { zodResolver } from '@hookform/resolvers/zod'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { useState } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { ApiError } from '../../api/client'
import {
  borradorQuery,
  useCrearBorrador,
  useEliminarBorrador,
  useEmitirBorrador,
  useGuardarBorrador,
} from '../../api/queries/borradores'
import { parametrosFacturacionQuery } from '../../api/queries/configuracionFacturacion'
import { useEmitirFactura } from '../../api/queries/facturas'
import type { BorradorSalida, FacturaSalida, ParametrosFacturacionSalida } from '../../api/tipos'
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
import { CamposFactura } from './CamposFactura'
import { ConfirmarEmisionDialog } from './ConfirmarEmisionDialog'
import { EnlacePresupuesto } from './EnlacePresupuesto'
import {
  aCuerpo,
  aCuerpoBorrador,
  campoDelServidor,
  erroresParaEmitir,
  esquema,
  etiquetaCliente,
  valoresDelBorrador,
  valoresIniciales,
  type ValoresFactura,
} from './factura-valores'

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

interface FormularioProps {
  parametros: ParametrosFacturacionSalida
  /** Sin borrador: factura nueva. Con él: modo borrador (FR-038). */
  borrador?: BorradorSalida | undefined
  onCerrar: () => void
  onEmitida: (factura: FacturaSalida) => void
  /** Tras «Guardar borrador» en una factura nueva, el modal pasa al modo borrador (FR-049). */
  onBorradorCreado: (borrador: BorradorSalida) => void
}

function FormularioFactura({
  parametros,
  borrador,
  onCerrar,
  onEmitida,
  onBorradorCreado,
}: FormularioProps) {
  const queryClient = useQueryClient()
  const emitirNueva = useEmitirFactura()
  const emitirBorrador = useEmitirBorrador()
  const crearBorrador = useCrearBorrador()
  const guardarBorrador = useGuardarBorrador()
  const eliminarBorrador = useEliminarBorrador()
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
  const form = useForm<ValoresFactura>({
    resolver: zodResolver(esquema),
    defaultValues: borrador ? valoresDelBorrador(borrador) : valoresIniciales(parametros.hoy),
  })
  const { formState, setError: marcar } = form
  // Un borrador de oro de inversión no lleva IVA: el aviso de cambio de tipo no aplica (FR-052).
  const oroInversion = useWatch({ control: form.control, name: 'oro_inversion' })
  // Se lee al renderizar para que react-hook-form lo mantenga al día (su `formState` es un proxy).
  const sucio = formState.isDirty
  const ocupado =
    emitirNueva.isPending ||
    emitirBorrador.isPending ||
    crearBorrador.isPending ||
    guardarBorrador.isPending ||
    eliminarBorrador.isPending

  const intentarCerrar = () => {
    if (sucio) setDescartando(true)
    else onCerrar()
  }

  /** Vuelve a cargar el borrador guardado por otro (conflicto de versión, FR-020). */
  const recargar = async () => {
    if (!borrador) return
    await queryClient.invalidateQueries({ queryKey: borradorQuery(borrador.id).queryKey })
    const actual = await queryClient.query(borradorQuery(borrador.id))
    form.reset(valoresDelBorrador(actual))
    setVersion(actual.version)
    setTipoIvaPrevisto(actual.tipo_iva_previsto)
    setNombreCliente(actual.cliente ? etiquetaCliente(actual.cliente) : undefined)
    setConflicto(false)
    setError(null)
  }

  const mostrarError = (e: unknown, operacion: 'emitir' | 'guardar' | 'eliminar') => {
    if (!(e instanceof ApiError) || e.tipo === 'red') {
      // Se reintenta con la misma clave de operación: si la factura llegó a emitirse, la API
      // devuelve esa misma y no una segunda (FR-047).
      setError(
        operacion === 'emitir'
          ? 'No se ha podido completar la emisión. Tus datos siguen aquí: vuelve a intentarlo, sin riesgo de duplicar la factura.'
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
    } else if (e.tipo === 'fecha-expedicion') {
      marcar('fecha_expedicion', { message: e.message })
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
      const factura = borrador
        ? await emitirBorrador.mutateAsync({
            id: borrador.id,
            body: { ...aCuerpoBorrador(valores), version },
            clave,
          })
        : await emitirNueva.mutateAsync({ body: aCuerpo(valores), clave })
      renovar()
      setConfirmando(false)
      const origen = borrador?.presupuesto_origen
      toast(
        origen
          ? `Factura ${factura.num_serie} emitida. ${origen.num_serie} queda convertido`
          : `Factura ${factura.num_serie} emitida`,
      )
      onEmitida(factura)
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
      title={borrador ? 'Borrador' : 'Nueva factura'}
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
            Emitir factura
          </Button>
        </>
      }
    >
      <CamposFactura
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
        presupuestoOrigen={borrador?.presupuesto_origen}
        antes={
          <>
            <EnlacePresupuesto presupuesto={borrador?.presupuesto_origen} />
            {!oroInversion && tipoIvaPrevisto && tipoIvaPrevisto !== parametros.iva_por_defecto ? (
              <AvisoCambioIva previsto={tipoIvaPrevisto} vigente={parametros.iva_por_defecto} />
            ) : null}
          </>
        }
        despues={<Alerta mensaje={error} />}
      />
      <ConfirmarEmisionDialog
        isOpen={confirmando}
        onOpenChange={setConfirmando}
        onConfirmar={() => void confirmarEmision()}
        emitiendo={emitirNueva.isPending || emitirBorrador.isPending}
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
        Se borrará definitivamente. Como aún no es una factura, no consume ningún número ni deja
        registro de facturación.
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
          Hay cambios sin guardar en esta factura. Si cierras, se perderán.
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
              // Se cierra el modal entero sin cerrar antes la confirmación: así el foco vuelve a
              // quien abrió el modal y no a un campo que va a desaparecer (FR-039).
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
  'No se han podido cargar los datos de facturación. Cierra y vuelve a intentarlo.'

/** Modal «Nueva factura» sobre el listado (US2; FR-037 a FR-040, FR-046, FR-049). */
export function NuevaFacturaModal({
  onCerrar,
  onEmitida,
  onBorradorCreado,
}: {
  onCerrar: () => void
  onEmitida: (factura: FacturaSalida) => void
  onBorradorCreado: (borrador: BorradorSalida) => void
}) {
  const parametros = useQuery(parametrosFacturacionQuery)
  if (!parametros.data) {
    return (
      <CargandoModal
        titulo="Nueva factura"
        error={parametros.isError ? SIN_PARAMETROS : null}
        onCerrar={onCerrar}
      />
    )
  }
  return (
    <FormularioFactura
      parametros={parametros.data}
      onCerrar={onCerrar}
      onEmitida={onEmitida}
      onBorradorCreado={onBorradorCreado}
    />
  )
}

/** Modal «Borrador»: el mismo formulario con «Eliminar borrador» (US4; FR-019, FR-020, FR-038). */
export function BorradorModal({
  borradorId,
  onCerrar,
  onEmitida,
}: {
  borradorId: string
  onCerrar: () => void
  onEmitida: (factura: FacturaSalida) => void
}) {
  const parametros = useQuery(parametrosFacturacionQuery)
  // La ruta lo pide al abrir (nunca se edita sobre una copia antigua); los refrescos posteriores
  // no tocan el formulario: conserva lo escrito y el conflicto se avisa al guardar (FR-020).
  const borrador = useQuery(borradorQuery(borradorId))
  if (!parametros.data || !borrador.data) {
    const error = borrador.isError
      ? borrador.error instanceof ApiError && borrador.error.tipo === 'no-encontrado'
        ? YA_NO_EXISTE
        : borrador.error.message
      : parametros.isError
        ? SIN_PARAMETROS
        : null
    return <CargandoModal titulo="Borrador" error={error} onCerrar={onCerrar} />
  }
  return (
    <FormularioFactura
      key={borrador.data.id}
      parametros={parametros.data}
      borrador={borrador.data}
      onCerrar={onCerrar}
      onEmitida={onEmitida}
      onBorradorCreado={() => undefined}
    />
  )
}
