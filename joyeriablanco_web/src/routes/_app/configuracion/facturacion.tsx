import { createFileRoute } from '@tanstack/react-router'
import { FacturacionPage } from '../../../features/configuracion/FacturacionPage'

export const Route = createFileRoute('/_app/configuracion/facturacion')({
  component: FacturacionPage,
})
