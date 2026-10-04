import { useQuery } from '@tanstack/react-query'
import { Link, useRouterState } from '@tanstack/react-router'
import { TriangleAlert } from 'lucide-react'
import { useEffect } from 'react'
import { alarmasQuery } from '../../api/queries/registroFiscal'
import type { Alarma, Rol } from '../../api/tipos'

/** Dónde ve el administrador el detalle de cada alarma. */
function Detalle({ alarma }: { alarma: Alarma }) {
  const clase = 'shrink-0 text-danger underline underline-offset-4'
  if (alarma.tipo === 'certificado') {
    return (
      <Link to="/configuracion/facturacion" className={clase}>
        Ver detalle
      </Link>
    )
  }
  return (
    <Link to="/registro-fiscal" search={{ pestana: 'eventos', pagina: 1 }} className={clase}>
      Ver detalle
    </Link>
  )
}

/**
 * Banda de alarma (004, FR-019; Orden, art. 6.f): encima del contenido de todas las pantallas,
 * para cualquier usuario. Sin botón de cerrar: desaparece cuando la API deja de devolverla. Se
 * consulta al cambiar de ruta y cada minuto. Siempre con texto e icono, nunca solo con color.
 */
export function BandaAlarma({ rol }: { rol: Rol }) {
  const consulta = useQuery(alarmasQuery)
  const ruta = useRouterState({ select: (estado) => estado.location.pathname })
  const { refetch } = consulta
  useEffect(() => {
    void refetch()
  }, [ruta, refetch])

  const alarmas = [...(consulta.data?.alarmas ?? [])].sort((a, b) =>
    a.tipo === b.tipo ? 0 : a.tipo === 'integridad' ? -1 : 1,
  )
  if (alarmas.length === 0) return null
  return (
    <div className="flex flex-col">
      {alarmas.map((alarma) => (
        <div
          key={alarma.tipo}
          role="alert"
          className="flex flex-wrap items-start gap-3 border-b border-danger/40 bg-danger/8 px-margin-mobile py-3 body-md text-danger md:px-margin"
        >
          <TriangleAlert aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
          <p className="min-w-0 flex-1 break-words">{alarma.mensaje}.</p>
          {rol === 'administrador' ? <Detalle alarma={alarma} /> : null}
        </div>
      ))}
    </div>
  )
}
