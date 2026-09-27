import { ChevronDown } from 'lucide-react'
import {
  Button as AriaButton,
  FieldError,
  Label,
  ListBox,
  ListBoxItem,
  Popover,
  Select as AriaSelect,
  SelectValue,
  type Key,
} from 'react-aria-components'
import { cx } from './cx'
import { campoCaja, campoContenedor, campoError, campoEtiqueta } from './field'

export interface OpcionSelect {
  id: string
  label: string
}

export interface SelectProps {
  label: string
  options: readonly OpcionSelect[]
  value: string | null
  onChange: (value: string | null) => void
  placeholder?: string
  error?: string | undefined
  isRequired?: boolean
  isDisabled?: boolean
  hideLabel?: boolean
  className?: string
  name?: string
}

export function Select({
  label,
  options,
  value,
  onChange,
  placeholder = 'Selecciona…',
  error,
  isRequired,
  isDisabled,
  hideLabel = false,
  className,
  name,
}: SelectProps) {
  return (
    <AriaSelect
      aria-label={hideLabel ? label : undefined}
      name={name}
      value={value}
      onChange={(key: Key | null) => {
        onChange(key === null ? null : String(key))
      }}
      placeholder={placeholder}
      isRequired={isRequired}
      isDisabled={isDisabled}
      isInvalid={Boolean(error)}
      className={cx(campoContenedor, className)}
    >
      {hideLabel ? null : (
        <Label className={campoEtiqueta}>
          {label}
          {isRequired ? <span aria-hidden="true"> *</span> : null}
        </Label>
      )}
      <AriaButton
        className={cx(
          campoCaja,
          'flex items-center justify-between gap-2 text-left cursor-pointer',
          'data-[focus-visible]:border-primary-container data-[pressed]:border-primary-container',
        )}
      >
        <SelectValue className="truncate data-[placeholder]:text-on-surface-variant" />
        <ChevronDown aria-hidden="true" className="size-4 shrink-0 text-on-surface-variant" />
      </AriaButton>
      <FieldError className={campoError}>{error}</FieldError>
      <Popover className="min-w-(--trigger-width) border border-primary-container bg-surface-container-lowest shadow-nivel-2">
        <ListBox className="max-h-72 overflow-auto p-1 outline-none">
          {options.map((opcion) => (
            <ListBoxItem
              key={opcion.id}
              id={opcion.id}
              textValue={opcion.label}
              className="cursor-pointer px-3 py-2 body-md text-on-surface outline-none data-[focused]:bg-surface-container-high data-[selected]:text-primary"
            >
              {opcion.label}
            </ListBoxItem>
          ))}
        </ListBox>
      </Popover>
    </AriaSelect>
  )
}
