import { FieldError, Input, Label, Text, TextField as AriaTextField } from 'react-aria-components'
import { cx } from './cx'
import { campoAyuda, campoCaja, campoContenedor, campoError, campoEtiqueta } from './field'

export interface CampoFechaProps {
  label: string
  /** Fecha AAAA-MM-DD o `undefined` si está vacía. */
  value: string | undefined
  onChange: (valor: string | undefined) => void
  onBlur?: () => void
  min?: string
  max?: string
  error?: string | undefined
  description?: string
  isRequired?: boolean
  isDisabled?: boolean
  className?: string
}

/** Campo de fecha nativo con el tema oscuro de DESIGN.md (compartido por auditoría y facturas). */
export function CampoFecha({
  label,
  value,
  onChange,
  onBlur,
  min,
  max,
  error,
  description,
  isRequired = false,
  isDisabled = false,
  className,
}: CampoFechaProps) {
  return (
    <AriaTextField
      type="date"
      value={value ?? ''}
      onChange={(v) => {
        onChange(v || undefined)
      }}
      {...(onBlur ? { onBlur } : {})}
      isInvalid={Boolean(error)}
      isRequired={isRequired}
      isDisabled={isDisabled}
      className={cx(campoContenedor, className)}
    >
      <Label className={campoEtiqueta}>
        {label}
        {isRequired ? <span aria-hidden="true"> *</span> : null}
      </Label>
      <Input min={min} max={max} className={cx(campoCaja, '[color-scheme:dark]')} />
      {description && !error ? (
        <Text slot="description" className={campoAyuda}>
          {description}
        </Text>
      ) : null}
      <FieldError className={campoError}>{error}</FieldError>
    </AriaTextField>
  )
}
