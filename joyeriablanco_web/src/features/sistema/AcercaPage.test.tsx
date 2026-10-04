import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import type { SistemaSalida } from '../../api/tipos'
import { conSesion, crearSesion, renderApp } from '../../test/app'
import { server } from '../../test/msw'

const TITULO = 'DECLARACIÓN RESPONSABLE DEL SISTEMA INFORMÁTICO DE FACTURACIÓN'
const SISTEMA: SistemaSalida = {
  nombre: 'Joyería Blanco Gestión',
  id_sistema: 'JB',
  version: '0.4.0',
  numero_instalacion: '1',
  productor: {
    nombre: 'Joyería Blanco, S.L.',
    nif: 'B12345674',
    direccion: 'Calle Mayor, 1, 39001 Santander',
  },
  modalidad: 'no_verifactu',
  declaracion: {
    titulo: TITULO,
    apartados: 'abcdefghijkl'.split('').map((letra) => ({
      letra,
      texto: `Texto de la letra ${letra}`,
      valor: letra === 'e' || letra === 'f' ? 'No' : `Valor ${letra}`,
    })),
  },
}

describe('Acerca del sistema (004, FR-027, SC-008)', () => {
  beforeEach(() => {
    server.use(http.get('*/api/v1/sistema', () => HttpResponse.json(SISTEMA)))
  })

  it('un empleado ve los datos del sistema y la declaración con cada letra y su texto', async () => {
    conSesion(crearSesion({ rol: 'empleado' }))
    renderApp('/acerca')

    expect(await screen.findByRole('heading', { name: TITULO })).toBeInTheDocument()
    expect(screen.getByText('Joyería Blanco Gestión')).toBeInTheDocument()
    expect(screen.getByText('Joyería Blanco, S.L. · NIF B12345674')).toBeInTheDocument()
    const terminos = screen.getAllByRole('term').map((t) => t.textContent)
    expect(terminos).toEqual(
      expect.arrayContaining(['a) Texto de la letra a', 'l) Texto de la letra l']),
    )
    expect(screen.getAllByText('No')).toHaveLength(2)
    expect(
      screen.getByRole('link', { name: 'Descargar PDF de la declaración responsable' }),
    ).toHaveAttribute('href', '/api/v1/sistema/declaracion-responsable/pdf')
  })

  it('se llega desde el pie del menú lateral', async () => {
    conSesion(crearSesion({ rol: 'empleado' }))
    renderApp('/cuenta')
    const user = userEvent.setup()

    const [nav] = await screen.findAllByRole('navigation', { name: 'Navegación principal' })
    const lateral = nav?.parentElement
    if (!lateral) throw new Error('Sin menú lateral')
    await user.click(within(lateral).getByRole('link', { name: 'Acerca del sistema' }))

    expect(await screen.findByRole('heading', { name: 'Acerca del sistema' })).toBeInTheDocument()
  })

  it('y desde el menú de usuario, en dos clics', async () => {
    conSesion(crearSesion({ rol: 'empleado' }))
    renderApp('/cuenta')
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: /Opciones de usuario|Ana García/ }))
    await user.click(await screen.findByRole('menuitem', { name: 'Acerca del sistema' }))

    expect(await screen.findByRole('heading', { name: 'Acerca del sistema' })).toBeInTheDocument()
  })
})
