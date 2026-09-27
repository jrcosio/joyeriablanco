import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useCatalogos } from '../../../api/queries/catalogos'
import { useCrearCliente } from '../../../api/queries/clientes'
import { toast } from '../../../components/ui/toast-store'
import { ClientePanel } from '../../../features/clientes/ClientePanel'

export const Route = createFileRoute('/_app/clientes/nuevo')({
  component: NuevoCliente,
})

function NuevoCliente() {
  const navigate = useNavigate()
  const catalogos = useCatalogos()
  const crear = useCrearCliente()
  const cerrar = () => {
    void navigate({ to: '/clientes', search: (previa) => previa })
  }
  return (
    <ClientePanel
      catalogos={catalogos.data}
      onCerrar={cerrar}
      onGuardar={async (cuerpo) => {
        const creado = await crear.mutateAsync(cuerpo)
        toast(`Cliente «${creado.nombre}» creado.`)
        cerrar()
      }}
    />
  )
}
