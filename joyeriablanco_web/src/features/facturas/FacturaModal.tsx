import { zodResolver } from '@hookform/resolvers/zod'
import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { UserPlus } from 'lucide-react'
import { useState } from 'react'
import { Controller, useForm, useWatch, type UseFormReturn } from 'react-hook-form'
import { Form } from 'react-aria-components'
import { ApiError } from '../../api/client'
import { parametrosFacturacionQuery } from '../../api/queries/configuracionFacturacion'
import { useEmitirFactura } from '../../api/queries/facturas'
import type { FacturaSalida, ParametrosFacturacionSalida } from '../../api/tipos'
import { useSesion } from '../../auth/session'
import { Alerta } from '../../components/forms/Alerta'
import { Button } from '../../components/ui/Button'
import { CampoFecha } from '../../components/ui/CampoFecha'
import { Dialog } from '../../components/ui/Dialog'
import { ModalDocumento } from '../../components/ui/ModalDocumento'
import { Skeleton } from '../../components/ui/Skeleton'
import { toast } from '../../components/ui/toast-store'
import { ClienteAltaPanel } from '../clientes/ClienteAltaPanel'
import { calcularTotales, desdeApi } from '../../lib/dinero'
import { textoFalta } from '../../lib/facturacion'
import { useClaveOperacion } from '../../lib/idempotencia'
import { ConfirmarEmisionDialog } from './ConfirmarEmisionDialog'
import {
  aCuerpo,
  campoDelServidor,
  erroresParaEmitir,
  esquema,
  lineasCalculo,
  valoresIniciales,
  type ValoresFactura,
} from './factura-valores'
import { LineasFactura } from './LineasFactura'
import { ResumenCliente } from './ResumenCliente'
import { SelectorCliente } from './SelectorCliente'
import { TotalesFactura } from './TotalesFactura'

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

function FormularioFactura({
  parametros,
  onCerrar,
  onEmitida,
}: {
  parametros: ParametrosFacturacionSalida
  onCerrar: () => void
  onEmitida: (factura: FacturaSalida) => void
}) {
  const emitir = useEmitirFactura()
  const { clave, renovar } = useClaveOperacion()
  const [error, setError] = useState<string | null>(null)
  const [confirmando, setConfirmando] = useState(false)
  const [descartando, setDescartando] = useState(false)
  const [altaCliente, setAltaCliente] = useState(false)
  const [nombreCliente, setNombreCliente] = useState<string | undefined>(undefined)
  const form = useForm<ValoresFactura>({
    resolver: zodResolver(esquema),
    defaultValues: valoresIniciales(parametros.hoy),
  })
  const { control, formState, setError: marcar } = form
  const clienteId = useWatch({ control, name: 'cliente_id' })

  const intentarCerrar = () => {
    if (formState.isDirty) setDescartando(true)
    else onCerrar()
  }

  const mostrarError = (e: unknown) => {
    if (!(e instanceof ApiError) || e.tipo === 'red') {
      // Se reintenta con la misma clave de operación: si la factura llegó a emitirse, la API
      // devuelve esa misma y no una segunda (FR-047).
      setError(
        'No se ha podido completar la emisión. Tus datos siguen aquí: vuelve a intentarlo, sin riesgo de duplicar la factura.',
      )
      return
    }
    if (e.tipo === 'validacion' && e.problema.errores?.length) {
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
    try {
      const factura = await emitir.mutateAsync({ body: aCuerpo(form.getValues()), clave })
      renovar()
      setConfirmando(false)
      toast(`Factura ${factura.num_serie} emitida`)
      onEmitida(factura)
    } catch (e) {
      setConfirmando(false)
      mostrarError(e)
    }
  }

  return (
    <ModalDocumento
      title="Nueva factura"
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
          <Button
            onPress={() => void pedirEmision()}
            isDisabled={!parametros.emision_posible || emitir.isPending}
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
          setNombreCliente(`${cliente.nombre} · ${cliente.identificacion_numero}`)
          form.setValue('cliente_id', cliente.id, { shouldDirty: true, shouldValidate: true })
        }}
      />
      <ConfirmarEmisionDialog
        isOpen={confirmando}
        onOpenChange={setConfirmando}
        onConfirmar={() => void confirmarEmision()}
        emitiendo={emitir.isPending}
      />
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

/** Modal «Nueva factura» sobre el listado (US2; FR-037 a FR-040, FR-046, FR-049). */
export function NuevaFacturaModal({
  onCerrar,
  onEmitida,
}: {
  onCerrar: () => void
  onEmitida: (factura: FacturaSalida) => void
}) {
  const parametros = useQuery(parametrosFacturacionQuery)
  if (!parametros.data) {
    return (
      <ModalDocumento
        title="Nueva factura"
        isOpen
        onOpenChange={(abierto) => {
          if (!abierto) onCerrar()
        }}
      >
        {parametros.isError ? (
          <Alerta mensaje="No se han podido cargar los datos de facturación. Cierra y vuelve a intentarlo." />
        ) : (
          <div className="flex flex-col gap-5" aria-busy="true" aria-label="Cargando">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-40 w-full" />
          </div>
        )}
      </ModalDocumento>
    )
  }
  return (
    <FormularioFactura parametros={parametros.data} onCerrar={onCerrar} onEmitida={onEmitida} />
  )
}
