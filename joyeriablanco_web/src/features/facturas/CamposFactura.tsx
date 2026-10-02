import { UserPlus } from 'lucide-react'
import { useState } from 'react'
import { Controller, useWatch, type UseFormReturn } from 'react-hook-form'
import { Form } from 'react-aria-components'
import type { ParametrosFacturacionSalida } from '../../api/tipos'
import { Button } from '../../components/ui/Button'
import { CampoFecha } from '../../components/ui/CampoFecha'
import { Casilla } from '../../components/ui/Casilla'
import { fechaCorta } from '../../lib/fechas'
import { ClienteAltaPanel } from '../clientes/ClienteAltaPanel'
import { PrevisualizacionTotales, Seccion, SoloLectura } from '../documentos/CamposDocumento'
import { LineasDocumento } from '../documentos/LineasDocumento'
import { ResumenCliente } from '../documentos/ResumenCliente'
import { SelectorCliente } from '../documentos/SelectorCliente'
import { etiquetaCliente, type ValoresFactura } from './factura-valores'

/**
 * El formulario del modal de factura con sus tres secciones (FR-037): datos de emisión, detalle y
 * totales. Lo usan la factura nueva, el borrador y la modificación de una emitida; cada modo pone
 * su pie. El alta de cliente queda FUERA del `<form>`: su envío no debe llegar al de la factura
 * (los eventos de React atraviesan los portales).
 */
export function CamposFactura({
  form,
  parametros,
  fechaOperacion,
  numeroAyuda,
  nombreCliente,
  onNombreCliente,
  onSubmit,
  antes,
  despues,
}: {
  form: UseFormReturn<ValoresFactura>
  parametros: ParametrosFacturacionSalida
  /**
   * En una corrección, la fecha de la operación heredada de la original: la de expedición no puede
   * ser anterior (F-3 §3.1.3.1, error 1146; FR-018).
   */
  fechaOperacion?: string | undefined
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
  // FR-018: la fecha es libre dentro de los límites de la AEAT (fechas AAAA-MM-DD: se comparan como
  // texto).
  const minima = [parametros.fecha_minima, fechaOperacion]
    .filter((f): f is string => Boolean(f))
    .sort()
    .at(-1)

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
                  {...(minima ? { min: minima } : {})}
                  {...(fechaOperacion
                    ? {
                        description: `Fecha de la operación: ${fechaCorta(fechaOperacion)} (la de la original).`,
                      }
                    : {})}
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
          <LineasDocumento
            control={control}
            error={formState.errors.lineas?.root?.message ?? formState.errors.lineas?.message}
          />
        </Seccion>

        <div className="flex flex-col gap-4">
          <Controller
            control={control}
            name="oro_inversion"
            render={({ field }) => (
              <Casilla
                isSelected={field.value}
                onChange={field.onChange}
                className="w-full md:ml-auto md:max-w-sm"
              >
                Sin IVA (oro de inversión)
              </Casilla>
            )}
          />
          <PrevisualizacionTotales
            control={control}
            ivaPorDefecto={parametros.iva_por_defecto}
            mencionExencion={parametros.mencion_exencion_oro_inversion}
          />
        </div>
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
