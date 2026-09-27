import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useCatalogos } from '../../../api/queries/catalogos'
import { useCrearCliente, useReactivarCliente } from '../../../api/queries/clientes'
import { Button } from '../../../components/ui/Button'
import { toast } from '../../../components/ui/toast-store'
import { ClientePanel } from '../../../features/clientes/ClientePanel'

export const Route = createFileRoute('/_app/clientes/nuevo')({
  component: NuevoCliente,
})

function NuevoCliente() {
  const navigate = useNavigate()
  const catalogos = useCatalogos()
  const crear = useCrearCliente()
  const reactivar = useReactivarCliente()
  const cerrar = () => {
    void navigate({ to: '/clientes', search: (previa) => previa })
  }
  return (
    <ClientePanel
      catalogos={catalogos.data}
      onCerrar={cerrar}
      accionDuplicado={(existente) =>
        existente.activo ? null : (
          <Button
            variant="secondary"
            className="h-auto px-0 py-0 border-0"
            onPress={() => {
              void reactivar.mutateAsync(existente.id).then(() => {
                toast(`Cliente «${existente.nombre}» reactivado.`)
                void navigate({
                  to: '/clientes/$clienteId',
                  params: { clienteId: existente.id },
                  search: (previa) => previa,
                })
              })
            }}
          >
            Reactivar
          </Button>
        )
      }
      onGuardar={async (cuerpo) => {
        const creado = await crear.mutateAsync(cuerpo)
        toast(`Cliente «${creado.nombre}» creado.`)
        cerrar()
      }}
    />
  )
}
