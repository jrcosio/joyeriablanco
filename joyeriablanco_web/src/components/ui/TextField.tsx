import {
  FieldError,
  Input,
  Label,
  Text,
  TextArea,
  TextField as AriaTextField,
  type TextFieldProps as AriaTextFieldProps,
} from 'react-aria-components'
import { cx } from './cx'
import { campoAyuda, campoCaja, campoContenedor, campoError, campoEtiqueta } from './field'

export interface TextFieldProps extends Omit<AriaTextFieldProps, 'className'> {
  label: string
  description?: string
  error?: string | undefined
  placeholder?: string
  multiline?: boolean
  className?: string
}

export function TextField({
  label,
  description,
  error,
  placeholder,
  multiline = false,
  className,
  ...props
}: TextFieldProps) {
  return (
    <AriaTextField
      {...props}
      isInvalid={Boolean(error) || props.isInvalid}
      className={cx(campoContenedor, className)}
    >
      <Label className={campoEtiqueta}>
        {label}
        {props.isRequired ? <span aria-hidden="true"> *</span> : null}
      </Label>
      {multiline ? (
        <TextArea placeholder={placeholder} className={cx(campoCaja, 'h-24 py-2 resize-y')} />
      ) : (
        <Input placeholder={placeholder} className={campoCaja} />
      )}
      {description && !error ? (
        <Text slot="description" className={campoAyuda}>
          {description}
        </Text>
      ) : null}
      <FieldError className={campoError}>{error}</FieldError>
    </AriaTextField>
  )
}
