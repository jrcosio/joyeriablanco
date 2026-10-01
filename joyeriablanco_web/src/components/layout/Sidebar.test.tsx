import { screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { conSesion, crearSesion, renderApp } from '../../test/app'

async function navegacion(): Promise<HTMLElement> {
  const [nav] = await screen.findAllByRole('navigation', { name: 'Navegación principal' })
  if (!nav) throw new Error('No hay navegación principal')
  return nav
}

describe('Sidebar', () => {
  it('muestra Facturas activa y Presupuestos deshabilitado como "Próximamente"', async () => {
    conSesion(crearSesion())
    renderApp('/clientes')

    const nav = await navegacion()
    expect(within(nav).getByRole('link', { name: 'Facturas' })).toHaveAttribute('href', '/facturas')
    const presupuestos = within(nav).getByText('Presupuestos').closest('[aria-disabled="true"]')
    expect(presupuestos).not.toBeNull()
    expect(presupuestos).toHaveTextContent('Próximamente')
    expect(within(nav).getByRole('link', { name: 'Clientes' })).toHaveAttribute(
      'aria-current',
      'page',
    )
  })

  it('oculta Configuración a los empleados', async () => {
    conSesion(crearSesion({ rol: 'empleado' }))
    renderApp('/clientes')

    const nav = await navegacion()
    expect(within(nav).queryByRole('link', { name: 'Configuración' })).toBeNull()
  })

  it('muestra Configuración a los administradores', async () => {
    conSesion(crearSesion({ rol: 'administrador' }))
    renderApp('/clientes')

    const nav = await navegacion()
    expect(within(nav).getByRole('link', { name: 'Configuración' })).toBeInTheDocument()
  })

  it('un empleado que abre Configuración ve la pantalla de acceso denegado', async () => {
    conSesion(crearSesion({ rol: 'empleado' }))
    renderApp('/configuracion')

    expect(await screen.findByRole('heading', { name: 'Acceso denegado' })).toBeInTheDocument()
  })

  it('una dirección inexistente muestra la página no encontrada', async () => {
    conSesion(crearSesion())
    renderApp('/no-existe')

    expect(await screen.findByRole('heading', { name: 'Página no encontrada' })).toBeInTheDocument()
  })
})
