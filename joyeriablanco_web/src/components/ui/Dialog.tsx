import { X } from 'lucide-react'
import type { ReactNode } from 'react'
import { Dialog as AriaDialog, Heading, Modal, ModalOverlay } from 'react-aria-components'
import { Button } from './Button'
import { cx } from './cx'

export const overlayClase =
  'fixed inset-0 z-40 flex bg-surface-container-lowest/80 backdrop-blur-[2px] ' +
  'data-[entering]:opacity-0 transition-opacity duration-150'

export interface DialogProps {
  title: string
  isOpen: boolean
  onOpenChange: (abierto: boolean) => void
  children: ReactNode
  /** Si es false, solo se cierra con una acción explícita (p. ej. contraseña temporal). */
  isDismissable?: boolean
  role?: 'dialog' | 'alertdialog'
  className?: string
}

/** Diálogo de nivel 2 (DESIGN.md §Elevation). */
export function Dialog({
  title,
  isOpen,
  onOpenChange,
  children,
  isDismissable = true,
  role = 'dialog',
  className,
}: DialogProps) {
  return (
    <ModalOverlay
      isOpen={isOpen}
      onOpenChange={onOpenChange}
      isDismissable={isDismissable}
      isKeyboardDismissDisabled={!isDismissable}
      className={cx(overlayClase, 'items-center justify-center p-4')}
    >
      <Modal
        className={cx(
          'w-full max-w-lg border border-tertiary/35 bg-surface-container-high shadow-nivel-2',
          className,
        )}
      >
        <AriaDialog role={role} className="outline-none">
          {({ close }) => (
            <div className="flex flex-col gap-4 p-6">
              <div className="flex items-start justify-between gap-4">
                <Heading slot="title" className="title-lg text-on-surface">
                  {title}
                </Heading>
                {isDismissable ? (
                  <Button
                    variant="ghost"
                    aria-label="Cerrar"
                    onPress={close}
                    className="-mr-3 -mt-2"
                  >
                    <X aria-hidden="true" className="size-4" />
                  </Button>
                ) : null}
              </div>
              {children}
            </div>
          )}
        </AriaDialog>
      </Modal>
    </ModalOverlay>
  )
}
