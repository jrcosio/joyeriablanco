import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { conSesion, crearSesion, problema, renderApp } from '../../test/app'
import { server } from '../../test/msw'

const yo = crearSesion({
  rol: 'administrador',
  nombre: 'Luis Martín',
  nombre_usuario: 'admin.demo',
})
const lucia = {
  ...yo.usuario,
  id: '0192f0c0-0000-7000-8000-0000000000aa',
  nombre: 'Lucía Moreno',
  nombre_usuario: 'lucia.moreno',
  rol: 'empleado' as const,
}

function conUsuarios() {
  server.use(http.get('*/api/v1/usuarios', () => HttpResponse.json([yo.usuario, lucia])))
}

describe('UsuariosPage (US5)', () => {
  it('muestra la contraseña temporal una sola vez tras el alta', async () => {
    conSesion(yo)
    conUsuarios()
    server.use(
      http.post('*/api/v1/usuarios', () =>
        HttpResponse.json(
          {
            usuario: {
              ...lucia,
              id: 'nuevo',
              nombre_usuario: 'pablo.ortega',
              nombre: 'Pablo Ortega',
            },
            contrasena_temporal: 'Ab3d-Ef5h-Jk7m-Np9q',
          },
          { status: 201 },
        ),
      ),
    )
    renderApp('/configuracion/usuarios')
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Nuevo usuario' }))
    await user.type(screen.getByRole('textbox', { name: 'Nombre' }), 'Pablo Ortega')
    await user.type(screen.getByLabelText(/Nombre de usuario/), 'pablo.ortega')
    await user.click(screen.getByRole('button', { name: 'Crear usuario' }))

    const dialogo = await screen.findByRole('alertdialog', { name: 'Contraseña temporal' })
    expect(within(dialogo).getByLabelText('Contraseña temporal')).toHaveTextContent(
      'Ab3d-Ef5h-Jk7m-Np9q',
    )
    expect(within(dialogo).getByText(/No volverá a mostrarse/)).toBeInTheDocument()
    expect(within(dialogo).queryByRole('button', { name: 'Cerrar' })).toBeNull()
    await user.click(within(dialogo).getByRole('button', { name: 'He anotado la contraseña' }))
    expect(screen.queryByText('Ab3d-Ef5h-Jk7m-Np9q')).toBeNull()
  })

  it('no ofrece cambiar el propio rol ni desactivarse', async () => {
    conSesion(yo)
    conUsuarios()
    renderApp('/configuracion/usuarios')
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Acciones para Luis Martín' }))

    const menu = await screen.findByRole('menu')
    expect(within(menu).getByRole('menuitem', { name: 'Cambiar a empleado' })).toHaveAttribute(
      'aria-disabled',
      'true',
    )
    expect(within(menu).getByRole('menuitem', { name: 'Desactivar' })).toHaveAttribute(
      'aria-disabled',
      'true',
    )
  })

  it('muestra el error del último administrador', async () => {
    conSesion(yo)
    conUsuarios()
    server.use(
      http.post('*/api/v1/usuarios/:id/desactivacion', () =>
        problema(
          409,
          'ultimo-administrador',
          'El sistema no puede quedarse sin ningún administrador activo.',
        ),
      ),
    )
    renderApp('/configuracion/usuarios')
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Acciones para Lucía Moreno' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Desactivar' }))
    await user.click(
      within(await screen.findByRole('alertdialog')).getByRole('button', { name: 'Desactivar' }),
    )

    expect(
      await screen.findByText('El sistema no puede quedarse sin ningún administrador activo.'),
    ).toBeInTheDocument()
  })
})
