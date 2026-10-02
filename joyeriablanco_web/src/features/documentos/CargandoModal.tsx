import { Alerta } from '../../components/forms/Alerta'
import { Button } from '../../components/ui/Button'
import { ModalDocumento } from '../../components/ui/ModalDocumento'
import { Skeleton } from '../../components/ui/Skeleton'

/** Modal de un documento mientras cargan sus datos, o con el error si no se pudieron cargar. */
export function CargandoModal({
  titulo,
  error,
  onCerrar,
}: {
  titulo: string
  error: string | null
  onCerrar: () => void
}) {
  return (
    <ModalDocumento
      title={titulo}
      isOpen
      onOpenChange={(abierto) => {
        if (!abierto) onCerrar()
      }}
      footer={
        error ? (
          <Button variant="ghost" onPress={onCerrar}>
            Cerrar
          </Button>
        ) : undefined
      }
    >
      {error ? (
        <Alerta mensaje={error} />
      ) : (
        <div className="flex flex-col gap-5" aria-busy="true" aria-label="Cargando">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      )}
    </ModalDocumento>
  )
}
