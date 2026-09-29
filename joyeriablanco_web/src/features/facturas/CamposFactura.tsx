import { UserPlus } from 'lucide-react'
import { useState } from 'react'
import { Controller, useWatch, type UseFormReturn } from 'react-hook-form'
import { Form } from 'react-aria-components'
import type { ParametrosFacturacionSalida } from '../../api/tipos'
import { Button } from '../../components/ui/Button'
import { CampoFecha } from '../../components/ui/CampoFecha'
import { calcularTotales, desdeApi } from '../../lib/dinero'
import { fechaCorta } from '../../lib/fechas'
import { ClienteAltaPanel } from '../clientes/ClienteAltaPanel'
import { etiquetaCliente, lineasCalculo, type ValoresFactura } from './factura-valores'
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

function SoloLectura({
  etiqueta,
  valor,
  ayuda,
}: {
  etiqueta: string
  valor: string
  ayuda?: React.ReactNode
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="label-md text-on-surface-variant">{etiqueta}</span>
      <span className="flex h-11 items-center border border-on-surface/12 bg-surface-container px-3 body-md text-on-surface-variant tabular-nums">
        {valor}
      </span>
      {ayuda ? <span className="body-sm text-on-surface-variant">{ayuda}</span> : null}
    </div>
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

/** Fecha editable (nueva y borrador, FR-018) o fijada por el servidor (correcciones). */
export type FechasFactura =
  { editable: true } | { editable: false; expedicion: string; operacion: string }

/**
 * El formulario del modal de factura con sus tres secciones (FR-037): datos de emisión, detalle y
 * totales. Lo usan la factura nueva, el borrador y la modificación de una emitida; cada modo pone
 * su pie. El alta de cliente queda FUERA del `<form>`: su envío no debe llegar al de la factura
 * (los eventos de React atraviesan los portales).
 */
export function CamposFactura({
  form,
  parametros,
  fechas,
  numeroAyuda,
  nombreCliente,
  onNombreCliente,
  onSubmit,
  antes,
  despues,
}: {
  form: UseFormReturn<ValoresFactura>
  parametros: ParametrosFacturacionSalida
  fechas: FechasFactura
  /** Ayuda bajo «Se asigna al emitir» (p. ej. el próximo número previsto). */
  numeroAyuda: React.ReactNode
  /** Texto del cliente ya elegido; el selector se vuelve a montar cuando cambia. */
  nombreCliente: string | undefined
  onNombreCliente: (nombre: string | undefined) => void
  /** Intro en un campo: la acción principal del modo. */
  onSubmit: () => void
  /** Avisos antes de las secciones y después de los totales (p. ej. errores). */
  antes?: React.ReactNode
  despues?: React.ReactNode
}) {
  const { control, formState } = form
  const clienteId = useWatch({ control, name: 'cliente_id' })
  const [altaCliente, setAltaCliente] = useState(false)

  return (
    <>
      <Form
        className="flex flex-col gap-8"
        validationBehavior="aria"
        onSubmit={(e) => {
          e.preventDefault()
          onSubmit()
        }}
      >
        {antes}
        <Seccion titulo="Datos de emisión">
          <div className="grid grid-cols-1 gap-5 md:grid-cols-[1fr_1fr_2fr]">
            <SoloLectura etiqueta="Nº de factura" valor="Se asigna al emitir" ayuda={numeroAyuda} />
            {fechas.editable ? (
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
            ) : (
              <SoloLectura
                etiqueta="Fecha"
                valor={fechaCorta(fechas.expedicion)}
                ayuda={`Fecha de la operación: ${fechaCorta(fechas.operacion)} (la de la original)`}
              />
            )}
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
        {despues}
      </Form>

      <ClienteAltaPanel
        isOpen={altaCliente}
        onCerrar={() => {
          setAltaCliente(false)
        }}
        onCreado={(cliente) => {
          setAltaCliente(false)
          onNombreCliente(etiquetaCliente(cliente))
          form.setValue('cliente_id', cliente.id, { shouldDirty: true, shouldValidate: true })
        }}
      />
    </>
  )
}
