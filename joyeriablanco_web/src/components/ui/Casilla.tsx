import { Check } from 'lucide-react'
import type { ReactNode } from 'react'
import { CheckboxButton, CheckboxField } from 'react-aria-components'

/** Casilla de verificación con caja de 1 px y radio 0 (tokens de DESIGN.md). */
export function Casilla({
  isSelected,
  onChange,
  children,
  isInvalid = false,
  isRequired = false,
  className,
}: {
  isSelected: boolean
  onChange: (marcada: boolean) => void
  children: ReactNode
  isInvalid?: boolean
  isRequired?: boolean
  className?: string
}) {
  return (
    <CheckboxField
      isSelected={isSelected}
      onChange={onChange}
      isInvalid={isInvalid}
      isRequired={isRequired}
      className={className}
    >
      <CheckboxButton className="group flex cursor-pointer items-start gap-3 outline-none">
        <span
          aria-hidden="true"
          className="mt-0.5 flex size-5 shrink-0 items-center justify-center border border-on-surface-variant bg-surface-container-low transition-colors group-data-[selected]:border-primary group-data-[selected]:bg-primary group-data-[focus-visible]:outline group-data-[focus-visible]:outline-1 group-data-[focus-visible]:outline-offset-2 group-data-[focus-visible]:outline-primary group-data-[invalid]:border-danger"
        >
          <Check className="size-3.5 text-on-primary opacity-0 group-data-[selected]:opacity-100" />
        </span>
        <span className="body-md text-on-surface">{children}</span>
      </CheckboxButton>
    </CheckboxField>
  )
}
