import type { EstadoCertificado } from '../../api/tipos'
import { Card } from '../../components/ui/Card'
import { Chip } from '../../components/ui/Chip'
import { MOTIVOS_CERTIFICADO } from '../../lib/facturacion'
import { fechaHora } from '../../lib/fechas'

function EstadoChip({ certificado }: { certificado: EstadoCertificado }) {
  if (certificado.estado === 'no_utilizable') return <Chip tone="danger">No utilizable</Chip>
  if (certificado.caduca_pronto) return <Chip tone="warning">Caduca pronto</Chip>
  return <Chip tone="success">Utilizable</Chip>
}

/**
 * Tarjeta «Certificado de firma» (004, FR-003; contracts/ui-rutas.md): sus datos y su estado, sin
 * ninguna acción, porque el certificado lo instala quien despliega. Nunca la contraseña ni la clave.
 */
export function TarjetaCertificado({ certificado }: { certificado: EstadoCertificado }) {
  return (
    <Card className="flex flex-col gap-4 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="label-md text-primary">Certificado de firma</h2>
        <EstadoChip certificado={certificado} />
      </div>
      {certificado.motivo ? (
        <p className="body-md text-danger">{MOTIVOS_CERTIFICADO[certificado.motivo]}.</p>
      ) : null}
      {certificado.titular ? (
        <dl className="grid grid-cols-1 gap-x-6 gap-y-2 body-md sm:grid-cols-[auto_1fr]">
          <dt className="text-on-surface-variant">Titular</dt>
          <dd>{certificado.titular}</dd>
          <dt className="text-on-surface-variant">Identificación</dt>
          <dd className="tabular-nums">{certificado.identificacion ?? '—'}</dd>
          <dt className="text-on-surface-variant">Emisor</dt>
          <dd>{certificado.emisor ?? '—'}</dd>
          <dt className="text-on-surface-variant">Válido desde</dt>
          <dd className="tabular-nums">
            {certificado.valido_desde ? fechaHora(certificado.valido_desde) : '—'}
          </dd>
          <dt className="text-on-surface-variant">Válido hasta</dt>
          <dd className="tabular-nums">
            {certificado.valido_hasta ? fechaHora(certificado.valido_hasta) : '—'}
            {certificado.dias_restantes === null
              ? null
              : ` (quedan ${String(certificado.dias_restantes)} días)`}
          </dd>
        </dl>
      ) : null}
      <p className="body-sm text-on-surface-variant">
        Lo instala quien despliega el sistema, fuera de la aplicación. Firma cada registro de
        facturación y de evento (modalidad No VERI*FACTU).
      </p>
    </Card>
  )
}
