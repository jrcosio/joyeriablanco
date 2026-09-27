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

const pablo = {
  ...lucia,
  id: '0192f0c0-0000-7000-8000-0000000000bb',
  nombre: 'Pablo Ortega',
  nombre_usuario: 'pablo.ortega',
  activo: false,
}

function conUsuarios() {
  server.use(http.get('*/api/v1/usuarios', () => HttpResponse.json([yo.usuario, lucia, pablo])))
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

  it('solo ofrece eliminar a los usuarios desactivados', async () => {
    conSesion(yo)
    conUsuarios()
    renderApp('/configuracion/usuarios')
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Acciones para Lucía Moreno' }))
    expect(
      within(await screen.findByRole('menu')).queryByRole('menuitem', { name: 'Eliminar' }),
    ).toBeNull()
    await user.keyboard('{Escape}')
    await user.click(screen.getByRole('button', { name: 'Acciones para Pablo Ortega' }))

    expect(
      within(await screen.findByRole('menu')).getByRole('menuitem', { name: 'Eliminar' }),
    ).toBeInTheDocument()
  })

  it('elimina un usuario desactivado tras escribir su nombre de usuario', async () => {
    conSesion(yo)
    conUsuarios()
    const eliminados: string[] = []
    server.use(
      http.delete('*/api/v1/usuarios/:id', ({ params }) => {
        eliminados.push(String(params.id))
        return new HttpResponse(null, { status: 204 })
      }),
    )
    renderApp('/configuracion/usuarios')
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Acciones para Pablo Ortega' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Eliminar' }))
    const dialogo = await screen.findByRole('alertdialog', { name: 'Eliminar usuario' })
    expect(within(dialogo).getByText(/se conservan/)).toBeInTheDocument()
    const boton = within(dialogo).getByRole('button', { name: 'Eliminar' })
    expect(boton).toBeDisabled()
    await user.type(within(dialogo).getByLabelText(/Escribe el nombre de usuario/), 'Pablo.Ortega')
    expect(boton).toBeEnabled()
    await user.click(boton)

    expect(await screen.findByText('Pablo Ortega eliminado.')).toBeInTheDocument()
    expect(eliminados).toEqual([pablo.id])
    expect(screen.queryByRole('alertdialog')).toBeNull()
  })

  it('muestra el error si el usuario se reactivó mientras tanto', async () => {
    conSesion(yo)
    conUsuarios()
    server.use(
      http.delete('*/api/v1/usuarios/:id', () =>
        problema(409, 'usuario-activo', 'Desactiva el usuario antes de eliminarlo.'),
      ),
    )
    renderApp('/configuracion/usuarios')
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Acciones para Pablo Ortega' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Eliminar' }))
    const dialogo = await screen.findByRole('alertdialog', { name: 'Eliminar usuario' })
    await user.type(within(dialogo).getByLabelText(/Escribe el nombre de usuario/), 'pablo.ortega')
    await user.click(within(dialogo).getByRole('button', { name: 'Eliminar' }))

    expect(
      await within(dialogo).findByText('Desactiva el usuario antes de eliminarlo.'),
    ).toBeInTheDocument()
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
