import { CircleCheck, TriangleAlert, X } from 'lucide-react'
import { useSyncExternalStore } from 'react'
import { cx } from './cx'
import { cerrarAviso, getAvisos, suscribir } from './toast-store'

export function ToastRegion() {
  const lista = useSyncExternalStore(suscribir, getAvisos)
  return (
    <div
      role="region"
      aria-label="Notificaciones"
      className="pointer-events-none fixed right-4 bottom-4 z-50 flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-2"
    >
      {lista.map((aviso) => (
        <div
          key={aviso.id}
          role={aviso.tone === 'error' ? 'alert' : 'status'}
          className="pointer-events-auto flex items-start gap-3 border border-primary-container bg-surface-container-lowest px-4 py-3"
        >
          {aviso.tone === 'error' ? (
            <TriangleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-danger" />
          ) : (
            <CircleCheck
              aria-hidden="true"
              className={cx(
                'mt-0.5 size-4 shrink-0',
                aviso.tone === 'success' ? 'text-success' : 'text-primary',
              )}
            />
          )}
          <p className="flex-1 body-md text-on-surface">{aviso.message}</p>
          <button
            type="button"
            aria-label="Cerrar aviso"
            className="text-on-surface-variant hover:text-on-surface"
            onClick={() => {
              cerrarAviso(aviso.id)
            }}
          >
            <X aria-hidden="true" className="size-4" />
          </button>
        </div>
      ))}
    </div>
  )
}
