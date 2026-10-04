import { createFileRoute } from '@tanstack/react-router'
import { AcercaPage } from '../../features/sistema/AcercaPage'

/** «Acerca del sistema» (004, FR-027): para cualquier sesión. */
export const Route = createFileRoute('/_app/acerca')({
  component: AcercaPage,
})
