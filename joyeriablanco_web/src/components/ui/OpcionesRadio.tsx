import {
  FieldError,
  Label,
  RadioButton,
  RadioField,
  RadioGroup,
  type RadioGroupProps,
} from 'react-aria-components'
import { cx } from './cx'
import { campoContenedor, campoError, campoEtiqueta } from './field'

export interface OpcionRadio {
  id: string
  label: string
  description?: string
}

/**
 * Elección única en tarjetas de filete de 1 px y radio 0 (contracts/ui-rutas.md de 002): la
 * elegida lleva el borde `primary-container` y la superficie de nivel superior.
 */
export function OpcionesRadio({
  label,
  options,
  value,
  onChange,
  error,
  isRequired = false,
  className,
  ...props
}: {
  label: string
  options: readonly OpcionRadio[]
  value: string | null
  onChange: (valor: string) => void
  error?: string | undefined
  isRequired?: boolean
  className?: string
} & Omit<RadioGroupProps, 'value' | 'onChange' | 'className' | 'children'>) {
  return (
    <RadioGroup
      {...props}
      value={value}
      onChange={onChange}
      isRequired={isRequired}
      isInvalid={Boolean(error)}
      className={cx(campoContenedor, className)}
    >
      <Label className={campoEtiqueta}>
        {label}
        {isRequired ? <span aria-hidden="true"> *</span> : null}
      </Label>
      <div className="flex flex-col gap-2">
        {options.map((opcion) => (
          <RadioField key={opcion.id} value={opcion.id}>
            <RadioButton
              className={cx(
                'group/opcion flex cursor-pointer items-start gap-3 border border-on-surface/12 bg-surface-container-low px-4 py-3 outline-none transition-colors',
                'data-[selected]:border-primary-container data-[selected]:bg-surface-container-high',
                'data-[focus-visible]:border-primary data-[hovered]:border-primary-container/60',
              )}
            >
              <span
                aria-hidden="true"
                className="mt-1 flex size-4 shrink-0 items-center justify-center border border-on-surface-variant group-data-[selected]/opcion:border-primary"
              >
                <span className="size-2 bg-primary opacity-0 group-data-[selected]/opcion:opacity-100" />
              </span>
              <span className="flex flex-col gap-1">
                <span className="body-md text-on-surface">{opcion.label}</span>
                {opcion.description ? (
                  <span className="body-sm text-on-surface-variant">{opcion.description}</span>
                ) : null}
              </span>
            </RadioButton>
          </RadioField>
        ))}
      </div>
      <FieldError className={campoError}>{error}</FieldError>
    </RadioGroup>
  )
}
