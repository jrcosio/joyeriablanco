import { ChevronDown } from 'lucide-react'
import {
  Button as AriaButton,
  ComboBox as AriaComboBox,
  FieldError,
  Group,
  Input,
  Label,
  ListBox,
  ListBoxItem,
  Popover,
  type Key,
} from 'react-aria-components'
import { cx } from './cx'
import { campoCaja, campoContenedor, campoError, campoEtiqueta } from './field'
import type { OpcionSelect } from './Select'

export interface ComboBoxProps {
  label: string
  options: readonly OpcionSelect[]
  value: string | null
  onChange: (value: string | null) => void
  error?: string | undefined
  isRequired?: boolean
  isDisabled?: boolean
  className?: string
}

/** Selector con búsqueda para listas largas (países). */
export function ComboBox({
  label,
  options,
  value,
  onChange,
  error,
  isRequired,
  isDisabled,
  className,
}: ComboBoxProps) {
  return (
    <AriaComboBox
      value={value}
      onChange={(key: Key | null) => {
        onChange(key === null ? null : String(key))
      }}
      defaultItems={options}
      isRequired={isRequired}
      isDisabled={isDisabled}
      isInvalid={Boolean(error)}
      menuTrigger="focus"
      className={cx(campoContenedor, className)}
    >
      <Label className={campoEtiqueta}>
        {label}
        {isRequired ? <span aria-hidden="true"> *</span> : null}
      </Label>
      <Group
        className={cx(
          campoCaja,
          'flex items-center gap-2 px-0 focus-within:border-primary-container',
        )}
      >
        <Input className="h-full min-w-0 flex-1 bg-transparent px-3 outline-none" />
        <AriaButton
          aria-label="Mostrar opciones"
          className="px-3 text-on-surface-variant outline-none"
        >
          <ChevronDown aria-hidden="true" className="size-4" />
        </AriaButton>
      </Group>
      <FieldError className={campoError}>{error}</FieldError>
      <Popover className="min-w-(--trigger-width) border border-primary-container bg-surface-container-lowest shadow-nivel-2">
        <ListBox<OpcionSelect> className="max-h-72 overflow-auto p-1 outline-none">
          {(opcion) => (
            <ListBoxItem
              id={opcion.id}
              textValue={opcion.label}
              className="cursor-pointer px-3 py-2 body-md text-on-surface outline-none data-[focused]:bg-surface-container-high data-[selected]:text-primary"
            >
              {opcion.label}
            </ListBoxItem>
          )}
        </ListBox>
      </Popover>
    </AriaComboBox>
  )
}
