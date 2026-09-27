import { createFileRoute } from '@tanstack/react-router'
import { MiCuentaPage } from '../../features/cuenta/MiCuentaPage'

export const Route = createFileRoute('/_app/cuenta')({
  component: MiCuentaPage,
})
