import { zodResolver } from '@hookform/resolvers/zod'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { TriangleAlert, UserPlus } from 'lucide-react'
import { useState } from 'react'
import { Controller, useForm, useWatch, type UseFormReturn } from 'react-hook-form'
import { Form } from 'react-aria-components'
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
import { CampoFecha } from '../../components/ui/CampoFecha'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { Dialog } from '../../components/ui/Dialog'
import { ModalDocumento } from '../../components/ui/ModalDocumento'
import { Skeleton } from '../../components/ui/Skeleton'
import { toast } from '../../components/ui/toast-store'
import { calcularTotales, desdeApi } from '../../lib/dinero'
import { textoFalta, textoTipoIva } from '../../lib/facturacion'
import { useClaveOperacion } from '../../lib/idempotencia'
import { ClienteAltaPanel } from '../clientes/ClienteAltaPanel'
import { ConfirmarEmisionDialog } from './ConfirmarEmisionDialog'
import {
  aCuerpo,
  aCuerpoBorrador,
  campoDelServidor,
  erroresParaEmitir,
  esquema,
  etiquetaCliente,
  lineasCalculo,
  valoresDelBorrador,
  valoresIniciales,
  type ValoresFactura,
} from './factura-valores'
import { LineasFactura } from './LineasFactura'
import { ResumenCliente } from './ResumenCliente'
import { SelectorCliente } from './SelectorCliente'
import { TotalesFactura } from './TotalesFactura'

const YA_NO_EXISTE =
  'Este borrador ya se ha emitido o se ha eliminado. Ciérralo y búscalo en el listado.'

function Seccion({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-4">
      <h3 className="title-lg text-on-surface">{titulo}</h3>
      {children}
    </section>
  )
}

/** Totales previstos en el navegador (R-11). Tras guardar mandan los del servidor. */
function Previsualizacion({
  form,
  tipoIva,
}: {
  form: UseFormReturn<ValoresFactura>
  tipoIva: string
}) {
  const lineas = useWatch({ control: form.control, name: 'lineas' })
  const totales = calcularTotales(lineasCalculo(lineas), desdeApi(tipoIva))
  return <TotalesFactura {...totales} tipoIva={tipoIva} />
}

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

/** Aviso de que el IVA por defecto cambió después de guardar el borrador (spec, casos límite). */
function AvisoCambioIva({ previsto, vigente }: { previsto: string; vigente: string }) {
  return (
    <div
      role="status"
      className="flex items-start gap-3 border border-warning/40 bg-warning/8 px-4 py-3"
    >
      <TriangleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-warning" />
      <p className="body-md text-on-surface">
        El IVA por defecto ha cambiado desde que se guardó este borrador (del{' '}
        {textoTipoIva(previsto)} al {textoTipoIva(vigente)}). Al emitirlo se aplicará el{' '}
        {textoTipoIva(vigente)}.
      </p>
    </div>
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
  const [altaCliente, setAltaCliente] = useState(false)
  const [nombreCliente, setNombreCliente] = useState<string | undefined>(
    borrador?.cliente ? etiquetaCliente(borrador.cliente) : undefined,
  )
  const form = useForm<ValoresFactura>({
    resolver: zodResolver(esquema),
    defaultValues: borrador ? valoresDelBorrador(borrador) : valoresIniciales(parametros.hoy),
  })
  const { control, formState, setError: marcar } = form
  // Se lee al renderizar para que react-hook-form lo mantenga al día (su `formState` es un proxy).
  const sucio = formState.isDirty
  const clienteId = useWatch({ control, name: 'cliente_id' })
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
      toast(`Factura ${factura.num_serie} emitida`)
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
      <Form
        className="flex flex-col gap-8"
        validationBehavior="aria"
        onSubmit={(e) => {
          e.preventDefault()
          void pedirEmision()
        }}
      >
        {tipoIvaPrevisto && tipoIvaPrevisto !== parametros.iva_por_defecto ? (
          <AvisoCambioIva previsto={tipoIvaPrevisto} vigente={parametros.iva_por_defecto} />
        ) : null}
        <Seccion titulo="Datos de emisión">
          <div className="grid grid-cols-1 gap-5 md:grid-cols-[1fr_1fr_2fr]">
            <div className="flex flex-col gap-1.5">
              <span className="label-md text-on-surface-variant">Nº de factura</span>
              <span className="flex h-11 items-center border border-on-surface/12 bg-surface-container px-3 body-md text-on-surface-variant">
                Se asigna al emitir
              </span>
              <span className="body-sm text-on-surface-variant">
                Previsto: <span className="tabular-nums">{parametros.proximo_numero}</span>
              </span>
            </div>
            <Controller
              control={control}
              name="fecha_expedicion"
              render={({ field, fieldState }) => (
                <CampoFecha
                  label="Fecha"
                  isRequired
                  value={field.value}
                  onChange={(v) => {
                    field.onChange(v ?? '')
                  }}
                  onBlur={field.onBlur}
                  max={parametros.hoy}
                  {...(parametros.fecha_minima ? { min: parametros.fecha_minima } : {})}
                  error={fieldState.error?.message}
                />
              )}
            />
            <div className="flex flex-col gap-2">
              <Controller
                control={control}
                name="cliente_id"
                render={({ field, fieldState }) => (
                  <SelectorCliente
                    key={nombreCliente ?? 'selector'}
                    value={field.value}
                    nombreInicial={nombreCliente}
                    onChange={(id) => {
                      field.onChange(id)
                    }}
                    error={fieldState.error?.message}
                  />
                )}
              />
              <div>
                <Button
                  variant="ghost"
                  className="h-9 px-0"
                  onPress={() => {
                    setAltaCliente(true)
                  }}
                >
                  <UserPlus aria-hidden="true" className="size-4" />
                  Nuevo cliente
                </Button>
              </div>
            </div>
          </div>
          {clienteId ? <ResumenCliente clienteId={clienteId} /> : null}
        </Seccion>

        <Seccion titulo="Detalle de la factura">
          <LineasFactura
            control={control}
            error={formState.errors.lineas?.root?.message ?? formState.errors.lineas?.message}
          />
        </Seccion>

        <Previsualizacion form={form} tipoIva={parametros.iva_por_defecto} />
        <Alerta mensaje={error} />
      </Form>

      <ClienteAltaPanel
        isOpen={altaCliente}
        onCerrar={() => {
          setAltaCliente(false)
        }}
        onCreado={(cliente) => {
          setAltaCliente(false)
          setNombreCliente(etiquetaCliente(cliente))
          form.setValue('cliente_id', cliente.id, { shouldDirty: true, shouldValidate: true })
        }}
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
              setDescartando(false)
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

function Cargando({
  titulo,
  error,
  onCerrar,
}: {
  titulo: string
  error: string | null
  onCerrar: () => void
}) {
  return (
    <ModalDocumento
      title={titulo}
      isOpen
      onOpenChange={(abierto) => {
        if (!abierto) onCerrar()
      }}
      footer={
        error ? (
          <Button variant="ghost" onPress={onCerrar}>
            Cerrar
          </Button>
        ) : undefined
      }
    >
      {error ? (
        <Alerta mensaje={error} />
      ) : (
        <div className="flex flex-col gap-5" aria-busy="true" aria-label="Cargando">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      )}
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
      <Cargando
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
  const borrador = useQuery({ ...borradorQuery(borradorId), refetchOnMount: 'always' })
  // El formulario se monta con los datos pedidos al abrir, nunca con los de una caché antigua; los
  // refrescos posteriores no lo tocan (conserva lo escrito, y el conflicto se avisa, FR-020).
  if (!parametros.data || !borrador.data || !borrador.isFetchedAfterMount) {
    const error = borrador.isError
      ? borrador.error instanceof ApiError && borrador.error.tipo === 'no-encontrado'
        ? YA_NO_EXISTE
        : borrador.error.message
      : parametros.isError
        ? SIN_PARAMETROS
        : null
    return <Cargando titulo="Borrador" error={error} onCerrar={onCerrar} />
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
