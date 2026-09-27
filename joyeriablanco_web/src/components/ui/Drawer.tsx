import { X } from 'lucide-react'
import type { ReactNode } from 'react'
import { Dialog as AriaDialog, Heading, Modal, ModalOverlay } from 'react-aria-components'
import { Button } from './Button'
import { cx } from './cx'
import { overlayClase } from './Dialog'

export interface DrawerProps {
  title: string
  subtitle?: ReactNode
  isOpen: boolean
  onOpenChange: (abierto: boolean) => void
  children: ReactNode
  footer?: ReactNode
}

/**
 * Panel lateral de nivel 2: 560 px a la derecha en escritorio y tableta, pantalla completa en
 * móvil (FR-059, contracts/ui-rutas.md).
 */
export function Drawer({ title, subtitle, isOpen, onOpenChange, children, footer }: DrawerProps) {
  return (
    <ModalOverlay
      isOpen={isOpen}
      onOpenChange={onOpenChange}
      isDismissable
      className={cx(overlayClase, 'justify-end')}
    >
      <Modal className="h-dvh w-full md:max-w-panel border-l border-tertiary/35 bg-surface-container-high shadow-nivel-2 data-[entering]:translate-x-8 transition-transform duration-200">
        <AriaDialog className="flex h-full flex-col outline-none">
          {({ close }) => (
            <>
              <header className="flex items-start justify-between gap-4 border-b border-primary-container/18 px-6 py-5">
                <div className="flex flex-col gap-1">
                  <Heading slot="title" className="headline-md text-on-surface">
                    {title}
                  </Heading>
                  {subtitle ? (
                    <div className="body-md text-on-surface-variant">{subtitle}</div>
                  ) : null}
                </div>
                <Button variant="icon" aria-label="Cerrar panel" onPress={close}>
                  <X aria-hidden="true" className="size-4" />
                </Button>
              </header>
              <div className="flex-1 overflow-y-auto px-6 py-6">{children}</div>
              {footer ? (
                <footer className="flex flex-col-reverse gap-3 border-t border-primary-container/18 px-6 py-4 sm:flex-row sm:justify-end">
                  {footer}
                </footer>
              ) : null}
            </>
          )}
        </AriaDialog>
      </Modal>
    </ModalOverlay>
  )
}
