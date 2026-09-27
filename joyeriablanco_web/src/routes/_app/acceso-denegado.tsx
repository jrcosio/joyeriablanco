import { createFileRoute } from '@tanstack/react-router'
import { AccesoDenegadoPage } from '../../components/pages/AccesoDenegadoPage'

export const Route = createFileRoute('/_app/acceso-denegado')({
  component: AccesoDenegadoPage,
})
