import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { useState } from 'react'
import { ApiError } from '../../api/client'
import { registroCadenaQuery } from '../../api/queries/registroFiscal'
import type { Salto } from '../../api/tipos'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { Chip } from '../../components/ui/Chip'
import { ErrorState } from '../../components/ui/ErrorState'
import { Skeleton } from '../../components/ui/Skeleton'
import { TextField } from '../../components/ui/TextField'
import { fechaHora } from '../../lib/fechas'
import { ChipComprobacion } from './EventosTab'

/** Un indicador del salto: su nombre y un chip «Correcto» o «Incorrecto» (Orden, art. 7.h). */
function Indicador({ nombre, correcto }: { nombre: string; correcto: boolean }) {
  return (
    <span className="flex items-center gap-2 body-sm text-on-surface-variant">
      {nombre}
      <Chip tone={correcto ? 'success' : 'danger'}>{correcto ? 'Correcto' : 'Incorrecto'}</Chip>
    </span>
  )
}

function SaltoRegistro({
  etiqueta,
  salto,
  onIr,
}: {
  etiqueta: string
  salto: Salto | null | undefined
  onIr: (secuencia: number) => void
}) {
  if (!salto) {
    return <p className="body-sm text-on-surface-variant">{etiqueta}: no hay.</p>
  }
  return (
    <div className="flex flex-wrap items-center gap-3">
      <Button
        variant="secondary"
        onPress={() => {
          onIr(salto.secuencia)
        }}
      >
        {etiqueta} (nº {salto.secuencia})
      </Button>
      <Indicador nombre="Encadenamiento" correcto={salto.encadenamiento_correcto} />
      <Indicador nombre="Fechas" correcto={salto.fechas_en_orden} />
    </div>
  )
}

function Registro({ secuencia, onIr }: { secuencia: number; onIr: (secuencia: number) => void }) {
  const consulta = useQuery(registroCadenaQuery(secuencia))
  if (consulta.isError) {
    return (
      <Card className="bg-surface-container-low">
        {consulta.error instanceof ApiError && consulta.error.status === 404 ? (
          <p role="alert" className="p-6 body-md text-on-surface-variant">
            No existe el registro nº {secuencia}.
          </p>
        ) : (
          <ErrorState message={consulta.error.message} />
        )}
      </Card>
    )
  }
  const registro = consulta.data
  if (!registro) {
    return (
      <div aria-busy="true" aria-label="Cargando el registro" className="flex flex-col gap-3">
        <Skeleton className="h-6 w-1/2" />
        <Skeleton className="h-5 w-full" />
      </div>
    )
  }
  return (
    <Card className="flex flex-col gap-5 bg-surface-container-low p-6">
      <h3 className="title-lg text-on-surface">
        Registro de {registro.tipo === 'alta' ? 'alta' : 'anulación'} nº {registro.secuencia}
      </h3>
      <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 body-md">
        <dt className="text-on-surface-variant">Factura</dt>
        <dd>
          <Link
            to="/facturas/$facturaId"
            params={{ facturaId: registro.factura_id }}
            search
            className="text-primary underline underline-offset-4 tabular-nums"
          >
            {registro.num_serie}
          </Link>
        </dd>
        <dt className="text-on-surface-variant">Generado</dt>
        <dd className="tabular-nums">{fechaHora(registro.fecha_hora_huso_gen)}</dd>
        <dt className="text-on-surface-variant">Firmado por</dt>
        <dd>{registro.certificado_titular ?? 'Sin firma (VERI*FACTU)'}</dd>
        <dt className="text-on-surface-variant">Huella</dt>
        <dd className="break-all font-mono body-sm tabular-nums">{registro.huella}</dd>
      </dl>
      <div className="flex flex-wrap gap-2">
        <ChipComprobacion
          correcto={registro.huella_correcta}
          si="Huella correcta"
          no="Huella incorrecta"
        />
        {registro.firma_correcta === null ? null : (
          <ChipComprobacion
            correcto={registro.firma_correcta}
            si="Firma correcta"
            no="Firma incorrecta"
          />
        )}
      </div>
      <div className="flex flex-col gap-3 border-t border-primary-container/18 pt-4">
        <SaltoRegistro etiqueta="Anterior" salto={registro.anterior} onIr={onIr} />
        <SaltoRegistro etiqueta="Siguiente" salto={registro.siguiente} onIr={onIr} />
      </div>
    </Card>
  )
}

/**
 * «Registro fiscal → Cadena» (FR-020; Orden, art. 7.h): un registro de facturación por su número
 * de secuencia, o el que llega desde una factura, con los saltos al anterior y al siguiente.
 */
export function CadenaTab({
  secuencia,
  onSecuencia,
}: {
  secuencia: number | undefined
  onSecuencia: (secuencia: number) => void
}) {
  const [texto, setTexto] = useState(secuencia ? String(secuencia) : '')
  const numero = Number(texto)
  const valido = /^\d+$/.test(texto) && numero >= 1
  return (
    <div className="flex flex-col gap-6">
      <form
        className="flex flex-wrap items-end gap-3"
        onSubmit={(evento) => {
          evento.preventDefault()
          if (valido) onSecuencia(numero)
        }}
      >
        <TextField
          label="Número de registro"
          value={texto}
          onChange={setTexto}
          inputMode="numeric"
          className="w-48"
          error={texto && !valido ? 'Escribe un número entero desde 1.' : undefined}
        />
        <Button type="submit" variant="secondary" isDisabled={!valido}>
          Ver registro
        </Button>
      </form>
      {secuencia ? (
        <Registro
          secuencia={secuencia}
          onIr={(destino) => {
            setTexto(String(destino))
            onSecuencia(destino)
          }}
        />
      ) : (
        <p className="body-md text-on-surface-variant">
          Escribe un número de registro, o llega aquí desde una factura con «Ver en la cadena».
        </p>
      )}
    </div>
  )
}
