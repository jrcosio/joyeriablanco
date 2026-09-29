import { X } from 'lucide-react'
import type { ReactNode } from 'react'
import { Dialog as AriaDialog, Heading, Modal, ModalOverlay } from 'react-aria-components'
import { Button } from './Button'
import { cx } from './cx'
import { overlayClase } from './Dialog'

export interface ModalDocumentoProps {
  title: string
  subtitle?: ReactNode
  isOpen: boolean
  /**
   * Se llama con `false` al pulsar Escape, fuera del modal o el aspa. El padre decide si cierra
   * o si pide antes confirmación para descartar cambios (FR-036).
   */
  onOpenChange: (abierto: boolean) => void
  children: ReactNode
  footer?: ReactNode
}

/**
 * Modal ancho para documentos (facturas y, más adelante, presupuestos): nivel 2 de DESIGN.md,
 * centrado de `max-w-5xl` en escritorio y a pantalla completa por debajo de 768 px, con cuerpo
 * desplazable y pie fijo (research R-13, FR-037, FR-040). React Aria atrapa y devuelve el foco y
 * apila bien otros modales abiertos encima (p. ej. el alta de cliente, FR-046).
 */
export function ModalDocumento({
  title,
  subtitle,
  isOpen,
  onOpenChange,
  children,
  footer,
}: ModalDocumentoProps) {
  return (
    <ModalOverlay
      isOpen={isOpen}
      onOpenChange={onOpenChange}
      isDismissable
      className={cx(overlayClase, 'items-stretch justify-center md:items-center md:p-6')}
    >
      <Modal
        className={cx(
          'flex h-dvh w-full flex-col border-tertiary/35 bg-surface-container-high shadow-nivel-2',
          'md:h-auto md:max-h-[calc(100dvh-3rem)] md:max-w-5xl md:border',
        )}
      >
        <AriaDialog className="flex min-h-0 flex-1 flex-col outline-none">
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
                <Button variant="icon" aria-label="Cerrar" onPress={close}>
                  <X aria-hidden="true" className="size-4" />
                </Button>
              </header>
              <div className="min-h-0 flex-1 overflow-y-auto px-6 py-6">{children}</div>
              {footer ? (
                <footer className="flex flex-col-reverse gap-3 border-t border-primary-container/18 px-6 py-4 sm:flex-row sm:flex-wrap sm:items-center sm:justify-end">
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
