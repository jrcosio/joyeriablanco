import { Plus, Trash2 } from 'lucide-react'
import { Controller, useFieldArray, useWatch, type Control } from 'react-hook-form'
import { Button } from '../../components/ui/Button'
import { CampoDecimal } from '../../components/ui/CampoDecimal'
import { TextField } from '../../components/ui/TextField'
import { formatearEuros, importeLinea } from '../../lib/dinero'
import { lineaVacia, lineasCalculo, MAX_LINEAS, type ValoresFactura } from './factura-valores'

/** Importe previsto de la línea (el que vale es el del servidor, FR-014). */
function ImporteLinea({ control, indice }: { control: Control<ValoresFactura>; indice: number }) {
  const linea = useWatch({ control, name: `lineas.${indice}` })
  const [calculo] = lineasCalculo([linea])
  const importe = calculo ? importeLinea(calculo.unidades, calculo.precio) : 0n
  return <span className="tabular-nums">{formatearEuros(importe)}</span>
}

/**
 * Detalle de la factura (FR-037, FR-049): tabla editable en escritorio y tarjetas apiladas en
 * móvil. Se puede quitar cualquier línea, también la última; con 100 no se añaden más.
 */
export function LineasFactura({
  control,
  error,
}: {
  control: Control<ValoresFactura>
  error?: string | undefined
}) {
  const { fields, append, remove } = useFieldArray({ control, name: 'lineas' })

  return (
    <div className="flex flex-col gap-4">
      {fields.length === 0 ? (
        <p className="border border-dashed border-primary-container/40 px-4 py-6 text-center body-md text-on-surface-variant">
          Añade la primera línea.
        </p>
      ) : (
        <div className="border border-primary-container/18 bg-surface-container-low">
          <div
            aria-hidden="true"
            className="hidden grid-cols-[7rem_1fr_10rem_8rem_3rem] gap-3 border-b border-primary-container/18 bg-surface-container px-4 py-3 label-md text-on-surface-variant md:grid"
          >
            <span>Unidades</span>
            <span>Descripción</span>
            <span>Precio unitario</span>
            <span className="text-right">Importe</span>
            <span />
          </div>
          <ul className="flex flex-col">
            {fields.map((campo, indice) => {
              const numero = (indice + 1).toString()
              return (
                <li
                  key={campo.id}
                  className="grid grid-cols-2 items-start gap-3 border-b border-primary-container/10 px-4 py-4 last:border-b-0 md:grid-cols-[7rem_1fr_10rem_8rem_3rem] md:py-3"
                >
                  <Controller
                    control={control}
                    name={`lineas.${indice}.unidades`}
                    render={({ field, fieldState }) => (
                      <CampoDecimal
                        label={`Unidades de la línea ${numero}`}
                        etiquetaOculta
                        value={field.value}
                        onChange={field.onChange}
                        onBlur={field.onBlur}
                        error={fieldState.error?.message}
                      />
                    )}
                  />
                  <Controller
                    control={control}
                    name={`lineas.${indice}.descripcion`}
                    render={({ field, fieldState }) => (
                      <TextField
                        label={`Descripción de la línea ${numero}`}
                        value={field.value}
                        onChange={field.onChange}
                        onBlur={field.onBlur}
                        error={fieldState.error?.message}
                        maxLength={500}
                        className="col-span-2 order-first md:order-none md:col-span-1 [&>label]:sr-only"
                      />
                    )}
                  />
                  <Controller
                    control={control}
                    name={`lineas.${indice}.precio_unitario`}
                    render={({ field, fieldState }) => (
                      <CampoDecimal
                        label={`Precio unitario sin IVA de la línea ${numero}`}
                        etiquetaOculta
                        moneda
                        value={field.value}
                        onChange={field.onChange}
                        onBlur={field.onBlur}
                        error={fieldState.error?.message}
                      />
                    )}
                  />
                  <div className="flex h-11 items-center justify-end body-md text-on-surface">
                    <span className="sr-only">Importe de la línea {numero}: </span>
                    <ImporteLinea control={control} indice={indice} />
                  </div>
                  <div className="flex h-11 items-center justify-end">
                    <Button
                      variant="danger"
                      aria-label={`Quitar la línea ${numero}`}
                      onPress={() => {
                        remove(indice)
                      }}
                    >
                      <Trash2 aria-hidden="true" className="size-4" />
                    </Button>
                  </div>
                </li>
              )
            })}
          </ul>
        </div>
      )}
      {error ? <p className="body-sm text-danger">{error}</p> : null}
      <div>
        <Button
          variant="secondary"
          isDisabled={fields.length >= MAX_LINEAS}
          onPress={() => {
            append(lineaVacia())
          }}
        >
          <Plus aria-hidden="true" className="size-4" />
          Añadir línea
        </Button>
      </div>
    </div>
  )
}
