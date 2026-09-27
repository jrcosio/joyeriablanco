import { createFileRoute } from '@tanstack/react-router'
import { UsuariosPage } from '../../../features/usuarios/UsuariosPage'

export const Route = createFileRoute('/_app/configuracion/usuarios')({
  component: UsuariosPage,
})
