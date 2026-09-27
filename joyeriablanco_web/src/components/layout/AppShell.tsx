import { X } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { Dialog, Modal, ModalOverlay } from 'react-aria-components'
import type { SesionSalida } from '../../api/tipos'
import { Button } from '../ui/Button'
import { overlayClase } from '../ui/Dialog'
import { Header } from './Header'
import { Sidebar } from './Sidebar'

/**
 * Estructura de la aplicación: menú lateral a la IZQUIERDA (decisión del responsable), cajón
 * por debajo de 1024 px (FR-038, FR-040).
 */
export function AppShell({ sesion, children }: { sesion: SesionSalida; children: ReactNode }) {
  const [cajonAbierto, setCajonAbierto] = useState(false)
  const rol = sesion.usuario.rol

  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[20rem_1fr]">
      <aside className="sticky top-0 hidden h-dvh border-r border-primary-container/18 lg:block">
        <Sidebar rol={rol} />
      </aside>

      <ModalOverlay
        isOpen={cajonAbierto}
        onOpenChange={setCajonAbierto}
        isDismissable
        className={`${overlayClase} lg:hidden`}
      >
        <Modal className="h-dvh w-80 max-w-[88vw] border-r border-primary-container/18">
          <Dialog aria-label="Navegación" className="relative h-full outline-none">
            <Button
              variant="icon"
              aria-label="Cerrar menú de navegación"
              className="absolute top-3 right-3 z-10"
              onPress={() => {
                setCajonAbierto(false)
              }}
            >
              <X aria-hidden="true" className="size-4" />
            </Button>
            <Sidebar
              rol={rol}
              onNavegar={() => {
                setCajonAbierto(false)
              }}
            />
          </Dialog>
        </Modal>
      </ModalOverlay>

      <div className="flex min-w-0 flex-col">
        <Header
          usuario={sesion.usuario}
          onAbrirMenu={() => {
            setCajonAbierto(true)
          }}
        />
        <main className="mx-auto w-full max-w-contenido flex-1 px-margin-mobile py-8 md:px-margin md:py-10">
          {children}
        </main>
      </div>
    </div>
  )
}
