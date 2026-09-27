import { Link } from '@tanstack/react-router'

/** Pantalla de página no encontrada (FR-041). */
export function NotFoundPage() {
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-4 px-6 text-center">
      <p className="label-md text-primary">Error 404</p>
      <h1 className="headline-xl-mobile md:headline-xl text-on-surface">Página no encontrada</h1>
      <p className="max-w-md body-lg text-on-surface-variant">
        La dirección que has abierto no existe o ha cambiado.
      </p>
      <Link
        to="/clientes"
        className="mt-4 inline-flex h-11 items-center bg-primary px-6 label-lg text-on-primary hover:bg-tertiary"
      >
        Volver a Clientes
      </Link>
    </main>
  )
}
