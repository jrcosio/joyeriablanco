import { useQuery } from '@tanstack/react-query'
import { sistemaQuery, URL_DECLARACION_PDF } from '../../api/queries/sistema'
import { PageHeader } from '../../components/layout/PageHeader'
import { Card } from '../../components/ui/Card'
import { ErrorState } from '../../components/ui/ErrorState'
import { Skeleton } from '../../components/ui/Skeleton'
import { EnlaceImprimir } from '../documentos/EnlaceImprimir'

/**
 * «Acerca del sistema» (004, FR-027 a FR-029; RRSIF, art. 13.2; Orden, art. 15): los datos del
 * sistema informático y su declaración responsable, con cada letra del art. 15.1 precedida de su
 * texto descriptivo. Para cualquier usuario, a dos clics desde cualquier pantalla (SC-008).
 */
export function AcercaPage() {
  const consulta = useQuery(sistemaQuery)
  const sistema = consulta.data
  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        title="Acerca del sistema"
        subtitle="Sistema informático de facturación y su declaración responsable."
      />
      {consulta.isError ? (
        <ErrorState message={consulta.error.message} onRetry={() => void consulta.refetch()} />
      ) : !sistema ? (
        <div aria-busy="true" aria-label="Cargando" className="flex flex-col gap-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      ) : (
        <>
          <Card className="flex flex-col gap-4 p-6">
            <h2 className="label-md text-primary">Sistema informático</h2>
            <dl className="grid grid-cols-1 gap-x-6 gap-y-2 body-md sm:grid-cols-[auto_1fr]">
              <dt className="text-on-surface-variant">Nombre</dt>
              <dd>{sistema.nombre}</dd>
              <dt className="text-on-surface-variant">Código identificador</dt>
              <dd className="tabular-nums">{sistema.id_sistema}</dd>
              <dt className="text-on-surface-variant">Versión</dt>
              <dd className="tabular-nums">{sistema.version}</dd>
              <dt className="text-on-surface-variant">Número de instalación</dt>
              <dd className="tabular-nums">{sistema.numero_instalacion}</dd>
              <dt className="text-on-surface-variant">Modalidad</dt>
              <dd>No VERI*FACTU</dd>
              <dt className="text-on-surface-variant">Productor</dt>
              <dd>
                {sistema.productor.nombre} · NIF {sistema.productor.nif}
              </dd>
            </dl>
          </Card>
          <Card className="flex flex-col gap-5 p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <h2 className="title-lg text-on-surface">{sistema.declaracion.titulo}</h2>
              <EnlaceImprimir
                href={URL_DECLARACION_PDF}
                etiqueta="Descargar PDF de la declaración responsable"
              >
                Descargar PDF
              </EnlaceImprimir>
            </div>
            <dl className="flex flex-col gap-4">
              {sistema.declaracion.apartados.map((a) => (
                <div key={a.letra} className="flex flex-col gap-1">
                  <dt className="body-sm text-on-surface-variant">
                    {a.letra}) {a.texto}
                  </dt>
                  <dd className="body-md text-on-surface">{a.valor}</dd>
                </div>
              ))}
            </dl>
          </Card>
        </>
      )}
    </div>
  )
}
