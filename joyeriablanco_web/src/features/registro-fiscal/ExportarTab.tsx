import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { ApiError } from '../../api/client'
import { descargarExportacion, type FiltrosExportacion } from '../../api/queries/registroFiscal'
import { Alerta } from '../../components/forms/Alerta'
import { Button } from '../../components/ui/Button'
import { CampoFecha } from '../../components/ui/CampoFecha'
import { OpcionesRadio } from '../../components/ui/OpcionesRadio'
import { claveDia } from '../../lib/fechas'

type Estado =
  | { tipo: 'inicial' }
  | { tipo: 'exportando' }
  | { tipo: 'hecho'; nombre: string }
  | { tipo: 'vacio' }
  | { tipo: 'error'; mensaje: string }

function guardar(nombre: string, contenido: Blob): void {
  const url = URL.createObjectURL(contenido)
  const enlace = document.createElement('a')
  enlace.href = url
  enlace.download = nombre
  document.body.append(enlace)
  enlace.click()
  enlace.remove()
  URL.revokeObjectURL(url)
}

/**
 * «Registro fiscal → Exportar» (FR-022 a FR-026): los registros de facturación o de evento de un
 * periodo de días completos, en hora de Madrid, con los dos extremos incluidos. Por defecto, el
 * mes en curso hasta hoy. Descarga un ZIP con cada registro tal como se firmó.
 */
export function ExportarTab() {
  const queryClient = useQueryClient()
  const hoy = claveDia(new Date())
  const [tipo, setTipo] = useState<FiltrosExportacion['tipo']>('facturacion')
  const [desde, setDesde] = useState<string | undefined>(`${hoy.slice(0, 8)}01`)
  const [hasta, setHasta] = useState<string | undefined>(hoy)
  const [estado, setEstado] = useState<Estado>({ tipo: 'inicial' })
  const errorHasta =
    desde && hasta && hasta < desde ? 'No puede ser anterior a «desde».' : undefined

  async function exportar() {
    if (!desde || !hasta || errorHasta) return
    setEstado({ tipo: 'exportando' })
    try {
      const { nombre, contenido } = await descargarExportacion({ tipo, desde, hasta })
      guardar(nombre, contenido)
      setEstado({ tipo: 'hecho', nombre })
      await queryClient.invalidateQueries({ queryKey: ['registro-fiscal'] })
    } catch (error) {
      if (error instanceof ApiError && error.tipo === 'sin-registros') {
        setEstado({ tipo: 'vacio' })
      } else {
        setEstado({
          tipo: 'error',
          mensaje: error instanceof Error ? error.message : 'No se ha podido exportar.',
        })
      }
    }
  }

  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <p className="body-md text-on-surface-variant">
        Descarga los registros de un periodo tal como se firmaron, para atender un requerimiento de
        la Administración. Exportar no borra ni altera nada: los registros siguen conservándose.
      </p>
      <form
        className="flex flex-col gap-4"
        onSubmit={(evento) => {
          evento.preventDefault()
          void exportar()
        }}
      >
        <OpcionesRadio
          label="Qué se exporta"
          value={tipo}
          onChange={(valor) => {
            setTipo(valor as FiltrosExportacion['tipo'])
          }}
          options={[
            { id: 'facturacion', label: 'Registros de facturación' },
            { id: 'eventos', label: 'Registros de evento' },
          ]}
        />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <CampoFecha label="Desde" value={desde} onChange={setDesde} isRequired />
          <CampoFecha
            label="Hasta"
            value={hasta}
            onChange={setHasta}
            isRequired
            error={errorHasta}
          />
        </div>
        <div>
          <Button
            type="submit"
            isDisabled={!desde || !hasta || Boolean(errorHasta) || estado.tipo === 'exportando'}
          >
            Exportar
          </Button>
        </div>
      </form>
      <div aria-live="polite">
        {estado.tipo === 'exportando' ? (
          <p className="body-md text-on-surface-variant">Exportando…</p>
        ) : null}
        {estado.tipo === 'hecho' ? (
          <p className="body-md text-on-surface">Descargado {estado.nombre}.</p>
        ) : null}
        {estado.tipo === 'vacio' ? (
          <p className="body-md text-on-surface-variant">No hay registros en ese periodo.</p>
        ) : null}
        {estado.tipo === 'error' ? <Alerta mensaje={estado.mensaje} /> : null}
      </div>
    </div>
  )
}
