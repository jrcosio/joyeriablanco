import { TriangleAlert } from 'lucide-react'

/** Mensaje de error de formulario (anunciado por lectores de pantalla). */
export function Alerta({ mensaje }: { mensaje: string | null }) {
  if (!mensaje) return null
  return (
    <div
      role="alert"
      className="flex items-start gap-3 border border-danger/40 bg-danger/8 px-4 py-3"
    >
      <TriangleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-danger" />
      <p className="body-md text-on-surface">{mensaje}</p>
    </div>
  )
}
