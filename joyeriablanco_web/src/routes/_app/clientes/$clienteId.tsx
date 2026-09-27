import { useQuery } from '@tanstack/react-query'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useCatalogos } from '../../../api/queries/catalogos'
import { clienteQuery, useEditarCliente } from '../../../api/queries/clientes'
import { ErrorState } from '../../../components/ui/ErrorState'
import { toast } from '../../../components/ui/toast-store'
import { ClientePanel } from '../../../features/clientes/ClientePanel'

export const Route = createFileRoute('/_app/clientes/$clienteId')({
  component: FichaCliente,
})

function FichaCliente() {
  const { clienteId } = Route.useParams()
  const navigate = useNavigate()
  const catalogos = useCatalogos()
  const ficha = useQuery(clienteQuery(clienteId))
  const editar = useEditarCliente(clienteId)
  const cerrar = () => {
    void navigate({ to: '/clientes', search: (previa) => previa })
  }

  if (ficha.isError) {
    return (
      <ErrorState
        message={ficha.error.message}
        onRetry={() => {
          void ficha.refetch()
        }}
      />
    )
  }

  return (
    <ClientePanel
      catalogos={catalogos.data}
      {...(ficha.data ? { cliente: ficha.data } : {})}
      cargando={ficha.isPending}
      onCerrar={cerrar}
      onGuardar={async (cuerpo) => {
        if (!ficha.data) return
        await editar.mutateAsync({ ...cuerpo, version: ficha.data.version })
        toast('Cambios guardados.')
        cerrar()
      }}
    />
  )
}
