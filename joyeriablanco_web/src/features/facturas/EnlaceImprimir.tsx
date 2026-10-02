import { Printer } from 'lucide-react'
import { useEffect, useRef, useState, type MouseEvent, type ReactNode } from 'react'
import { claseEnlaceSecundario } from '../../components/ui/enlace'
import { ESPERA_IMPRESION_MS } from '../../lib/impresion'

/**
 * Enlace que abre un PDF de la API en una pestaña nueva (003, research R-8). Tras el clic muestra
 * «Preparando…» y, durante 2 s, ignora otro clic para no abrir dos pestañas (FR-023). El estado se
 * anuncia a los lectores de pantalla (FR-031).
 */
export function EnlaceImprimir({
  href,
  etiqueta,
  children,
  className,
}: {
  href: string
  etiqueta: string
  children: ReactNode
  className?: string
}) {
  const [preparando, setPreparando] = useState(false)
  const temporizador = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(
    () => () => {
      if (temporizador.current) clearTimeout(temporizador.current)
    },
    [],
  )

  const alPulsar = (evento: MouseEvent<HTMLAnchorElement>) => {
    if (preparando) {
      evento.preventDefault()
      return
    }
    setPreparando(true)
    temporizador.current = setTimeout(() => {
      setPreparando(false)
    }, ESPERA_IMPRESION_MS)
  }

  return (
    <>
      <a
        href={href}
        target="_blank"
        rel="noopener"
        aria-label={etiqueta}
        onClick={alPulsar}
        className={className ? `${claseEnlaceSecundario} ${className}` : claseEnlaceSecundario}
      >
        <Printer aria-hidden="true" className="size-4 text-primary" />
        {preparando ? 'Preparando…' : children}
      </a>
      <span role="status" className="sr-only">
        {preparando ? 'Preparando el PDF…' : ''}
      </span>
    </>
  )
}
