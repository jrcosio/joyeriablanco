import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { TriangleAlert } from 'lucide-react'
import { clienteQuery } from '../../api/queries/clientes'
import { Skeleton } from '../../components/ui/Skeleton'

export interface DatosDestinatario {
  nombre: string
  identificacion_numero: string
  direccion: string | null
  codigo_postal: string | null
  localidad: string | null
  provincia: string | null
}

function Dato({
  etiqueta,
  valor,
  className,
}: {
  etiqueta: string
  valor: string | null
  className?: string
}) {
  return (
    <div className={className}>
      <dt className="label-sm text-on-surface-variant">{etiqueta}</dt>
      <dd className="body-md text-on-surface">{valor ?? '—'}</dd>
    </div>
  )
}

/** Datos fiscales del destinatario (FR-037), nivel 1 con filete de 1 px. */
export function FichaDestinatario({ datos }: { datos: DatosDestinatario }) {
  return (
    <dl className="grid grid-cols-1 gap-4 border border-primary-container/18 bg-surface-container p-5 sm:grid-cols-2 lg:grid-cols-4">
      <Dato
        etiqueta="Nombre o razón social"
        valor={datos.nombre}
        className="sm:col-span-2 lg:col-span-4"
      />
      <Dato etiqueta="NIF / identificación" valor={datos.identificacion_numero} />
      <Dato etiqueta="Dirección" valor={datos.direccion} />
      <Dato
        etiqueta="Localidad"
        valor={[datos.codigo_postal, datos.localidad].filter(Boolean).join(' ') || null}
      />
      <Dato etiqueta="Provincia" valor={datos.provincia} />
    </dl>
  )
}

/** Resumen del cliente elegido (datos actuales de su ficha) con aviso si no es facturable. */
export function ResumenCliente({ clienteId }: { clienteId: string }) {
  const consulta = useQuery(clienteQuery(clienteId))
  if (!consulta.data) {
    return <Skeleton className="h-32 w-full" />
  }
  const cliente = consulta.data
  const sinDomicilio = !cliente.direccion || !cliente.codigo_postal || !cliente.localidad
  return (
    <div className="flex flex-col gap-3">
      <FichaDestinatario
        datos={{
          nombre: cliente.nombre,
          identificacion_numero: cliente.identificacion_numero,
          direccion: cliente.direccion,
          codigo_postal: cliente.codigo_postal,
          localidad: cliente.localidad,
          provincia: cliente.provincia_nombre ?? cliente.provincia_texto,
        }}
      />
      {sinDomicilio || !cliente.activo ? (
        <div
          role="status"
          className="flex items-start gap-3 border border-warning/40 bg-warning/8 px-4 py-3"
        >
          <TriangleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-warning" />
          <p className="body-md text-on-surface">
            {cliente.activo
              ? 'A este cliente le falta el domicilio completo (dirección, código postal y localidad): no se podrá emitir hasta completarlo.'
              : 'Este cliente está desactivado: no se puede emitir a su nombre.'}{' '}
            <Link
              to="/clientes/$clienteId"
              params={{ clienteId: cliente.id }}
              className="text-primary underline underline-offset-4"
            >
              Abrir la ficha del cliente
            </Link>
          </p>
        </div>
      ) : null}
    </div>
  )
}
