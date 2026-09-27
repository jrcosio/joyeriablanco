import { Link } from '@tanstack/react-router'
import { ShieldAlert } from 'lucide-react'

/** Pantalla de acceso denegado (FR-041). */
export function AccesoDenegadoPage() {
  return (
    <section className="flex flex-col items-center gap-4 py-16 text-center">
      <ShieldAlert aria-hidden="true" className="size-10 text-primary-container" />
      <p className="label-md text-primary">Error 403</p>
      <h1 className="headline-xl-mobile text-on-surface md:headline-xl">Acceso denegado</h1>
      <p className="max-w-md body-lg text-on-surface-variant">
        Tu usuario no tiene permiso para ver esta sección. Si crees que es un error, consulta con un
        administrador.
      </p>
      <Link
        to="/clientes"
        className="mt-4 inline-flex h-11 items-center bg-primary px-6 label-lg text-on-primary hover:bg-tertiary"
      >
        Volver a Clientes
      </Link>
    </section>
  )
}
