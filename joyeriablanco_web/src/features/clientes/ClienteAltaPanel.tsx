import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useCatalogos } from '../../api/queries/catalogos'
import { clienteQuery, useCrearCliente, useReactivarCliente } from '../../api/queries/clientes'
import type { ClienteSalida } from '../../api/tipos'
import { Button } from '../../components/ui/Button'
import { toast } from '../../components/ui/toast-store'
import type { ClienteExistente } from './ClienteForm'
import { ClientePanel } from './ClientePanel'

/**
 * Alta de cliente controlada por props, para abrirla por encima de otra pantalla (p. ej. del
 * modal de factura, FR-046). Usa el mismo panel y el mismo formulario que Clientes (001), con
 * sus validaciones y su aviso de duplicado; como salir de aquí perdería el documento de debajo,
 * el duplicado no enlaza a su ficha sino que se puede usar (y reactivar si está inactivo).
 */
export function ClienteAltaPanel({
  isOpen,
  onCreado,
  onCerrar,
}: {
  isOpen: boolean
  /** Cliente para el documento: el recién creado o el existente que se ha elegido usar. */
  onCreado: (cliente: ClienteSalida) => void
  onCerrar: () => void
}) {
  const queryClient = useQueryClient()
  const catalogos = useCatalogos()
  const crear = useCrearCliente()
  const reactivar = useReactivarCliente()
  const [usando, setUsando] = useState(false)
  if (!isOpen) return null

  const usarExistente = async (existente: ClienteExistente) => {
    setUsando(true)
    try {
      if (existente.activo) {
        onCreado(await queryClient.query(clienteQuery(existente.id)))
      } else {
        const reactivado = await reactivar.mutateAsync(existente.id)
        toast(`Cliente «${reactivado.nombre}» reactivado.`)
        onCreado(reactivado)
      }
    } catch {
      toast('No se ha podido usar el cliente existente. Inténtalo de nuevo.', 'error')
    } finally {
      setUsando(false)
    }
  }

  return (
    <ClientePanel
      catalogos={catalogos.data}
      onCerrar={onCerrar}
      enlaceDuplicado={false}
      accionDuplicado={(existente) => (
        <Button
          variant="secondary"
          className="h-auto px-0 py-0 border-0"
          isDisabled={usando}
          onPress={() => void usarExistente(existente)}
        >
          {existente.activo ? 'Usar este cliente' : 'Reactivar y usar'}
        </Button>
      )}
      onGuardar={async (cuerpo) => {
        const creado = await crear.mutateAsync(cuerpo)
        toast(`Cliente «${creado.nombre}» creado.`)
        onCreado(creado)
      }}
    />
  )
}
