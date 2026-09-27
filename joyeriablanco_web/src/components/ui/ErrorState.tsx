import { TriangleAlert } from 'lucide-react'
import { Button } from './Button'

export interface ErrorStateProps {
  message?: string
  onRetry?: () => void
}

/** Aviso de error de red o servidor con opción de reintentar (FR-057). */
export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div role="alert" className="flex flex-col items-center gap-3 px-6 py-12 text-center">
      <TriangleAlert aria-hidden="true" className="size-8 text-danger" />
      <p className="title-md text-on-surface">No se han podido cargar los datos</p>
      <p className="max-w-md body-md text-on-surface-variant">
        {message ?? 'Se ha producido un error de conexión con el servidor.'}
      </p>
      {onRetry ? (
        <Button variant="secondary" onPress={onRetry} className="mt-2">
          Reintentar
        </Button>
      ) : null}
    </div>
  )
}
