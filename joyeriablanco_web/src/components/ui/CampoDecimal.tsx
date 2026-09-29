import { FieldError, Input, Label, Text, TextField as AriaTextField } from 'react-aria-components'
import { cx } from './cx'
import { campoAyuda, campoCaja, campoContenedor, campoError, campoEtiqueta } from './field'

export interface CampoDecimalProps {
  label: string
  /** Texto tal como lo escribe el usuario (formato español). Se interpreta con `lib/dinero.ts`. */
  value: string
  onChange: (valor: string) => void
  onBlur?: () => void
  /** Muestra el símbolo € de ancho fijo (DESIGN.md §Monetary Inputs). */
  moneda?: boolean
  /** Etiqueta solo para lectores de pantalla (p. ej. en las celdas de la tabla de líneas). */
  etiquetaOculta?: boolean
  error?: string | undefined
  description?: string
  isRequired?: boolean
  isDisabled?: boolean
  className?: string
}

/** Campo de cifra con coma decimal, cifras tabulares y, si es un importe, el símbolo €. */
export function CampoDecimal({
  label,
  value,
  onChange,
  onBlur,
  moneda = false,
  etiquetaOculta = false,
  error,
  description,
  isRequired = false,
  isDisabled = false,
  className,
}: CampoDecimalProps) {
  return (
    <AriaTextField
      value={value}
      onChange={onChange}
      {...(onBlur ? { onBlur } : {})}
      inputMode="decimal"
      autoComplete="off"
      isInvalid={Boolean(error)}
      isRequired={isRequired}
      isDisabled={isDisabled}
      className={cx(campoContenedor, className)}
    >
      <Label className={etiquetaOculta ? 'sr-only' : campoEtiqueta}>
        {label}
        {isRequired && !etiquetaOculta ? <span aria-hidden="true"> *</span> : null}
      </Label>
      <div className="relative">
        {moneda ? (
          <span
            aria-hidden="true"
            className="pointer-events-none absolute inset-y-0 right-3 flex w-4 items-center justify-center body-md text-primary-container"
          >
            €
          </span>
        ) : null}
        <Input className={cx(campoCaja, 'text-right tabular-nums', moneda && 'pr-9')} />
      </div>
      {description && !error ? (
        <Text slot="description" className={campoAyuda}>
          {description}
        </Text>
      ) : null}
      <FieldError className={campoError}>{error}</FieldError>
    </AriaTextField>
  )
}
