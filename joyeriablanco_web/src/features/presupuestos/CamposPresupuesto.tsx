import { UserPlus } from 'lucide-react'
import { useRef, useState } from 'react'
import { Controller, useWatch, type UseFormReturn } from 'react-hook-form'
import { Form } from 'react-aria-components'
import type { ParametrosPresupuestoSalida } from '../../api/tipos'
import { Button } from '../../components/ui/Button'
import { CampoFecha } from '../../components/ui/CampoFecha'
import { Casilla } from '../../components/ui/Casilla'
import { sumarDias } from '../../lib/fechas'
import { ClienteAltaPanel } from '../clientes/ClienteAltaPanel'
import { PrevisualizacionTotales, Seccion, SoloLectura } from '../documentos/CamposDocumento'
import { etiquetaCliente } from '../documentos/documento-valores'
import { LineasDocumento } from '../documentos/LineasDocumento'
import { ResumenCliente } from '../documentos/ResumenCliente'
import { SelectorCliente } from '../documentos/SelectorCliente'
import type { ValoresPresupuesto } from './presupuesto-valores'

/** El presupuesto se emite sin domicilio; la factura que salga de él, no (FR-011). */
export const AVISO_DOMICILIO_PRESUPUESTO =
  'A este cliente le falta el domicilio completo (dirección, código postal y localidad): el presupuesto se puede emitir, pero la factura convertida no se podrá emitir hasta completarlo.'

/**
 * El formulario del modal de presupuesto (FR-026): datos del presupuesto, detalle y totales. Lo
 * usan el presupuesto nuevo, el borrador y la modificación. Como en la factura, el alta de cliente
 * queda FUERA del `<form>`.
 *
 * «Válido hasta» propone la fecha más la validez por defecto, y se recalcula al cambiar la fecha
 * mientras el usuario no lo haya tocado (FR-009).
 */
export function CamposPresupuesto({
  form,
  parametros,
  numeroAyuda,
  nombreCliente,
  onNombreCliente,
  onSubmit,
  antes,
  despues,
}: {
  form: UseFormReturn<ValoresPresupuesto>
  parametros: ParametrosPresupuestoSalida
  numeroAyuda: React.ReactNode
  nombreCliente: string | undefined
  onNombreCliente: (nombre: string | undefined) => void
  onSubmit: () => void
  antes?: React.ReactNode
  despues?: React.ReactNode
}) {
  const { control, formState } = form
  const clienteId = useWatch({ control, name: 'cliente_id' })
  const [altaCliente, setAltaCliente] = useState(false)
  // Si la validez no se ha elegido a mano, sigue a la fecha. Un borrador guardado con otra validez
  // que la propuesta la conserva.
  const inicial = formState.defaultValues
  const validezManual = useRef(
    Boolean(
      inicial?.fecha &&
      inicial.valido_hasta &&
      inicial.valido_hasta !== sumarDias(inicial.fecha, parametros.validez_dias),
    ),
  )

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
        <Seccion titulo="Datos del presupuesto">
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-[1fr_1fr_1fr_2fr]">
            <SoloLectura
              etiqueta="Nº de presupuesto"
              valor="Se asigna al emitir"
              ayuda={numeroAyuda}
            />
            <Controller
              control={control}
              name="fecha"
              render={({ field, fieldState }) => (
                <CampoFecha
                  label="Fecha"
                  isRequired
                  value={field.value}
                  onChange={(v) => {
                    field.onChange(v ?? '')
                    if (v && !validezManual.current) {
                      form.setValue('valido_hasta', sumarDias(v, parametros.validez_dias), {
                        shouldDirty: true,
                        shouldValidate: formState.isSubmitted,
                      })
                    }
                  }}
                  onBlur={field.onBlur}
                  max={parametros.hoy}
                  min={parametros.fecha_minima}
                  error={fieldState.error?.message}
                />
              )}
            />
            <Controller
              control={control}
              name="valido_hasta"
              render={({ field, fieldState }) => (
                <CampoFecha
                  label="Válido hasta"
                  isRequired
                  value={field.value}
                  onChange={(v) => {
                    validezManual.current = true
                    field.onChange(v ?? '')
                  }}
                  onBlur={field.onBlur}
                  description={`Por defecto, ${String(parametros.validez_dias)} días.`}
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
          {clienteId ? (
            <ResumenCliente clienteId={clienteId} avisoDomicilio={AVISO_DOMICILIO_PRESUPUESTO} />
          ) : null}
        </Seccion>

        <Seccion titulo="Detalle del presupuesto">
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
            titulo="Total presupuesto"
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
