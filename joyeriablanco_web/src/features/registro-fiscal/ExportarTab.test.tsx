import { fireEvent, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { conSesion, crearSesion, problema, renderApp } from '../../test/app'
import { server } from '../../test/msw'
import { claveDia } from '../../lib/fechas'

const admin = crearSesion({ rol: 'administrador' })

function conExportacion(vacio = false) {
  const peticiones: URLSearchParams[] = []
  server.use(
    http.get('*/api/v1/registro-fiscal/eventos', () =>
      HttpResponse.json({ elementos: [], total: 0, pagina: 1, tamano: 25 }),
    ),
    http.get('*/api/v1/registro-fiscal/exportacion', ({ request }) => {
      const parametros = new URL(request.url).searchParams
      peticiones.push(parametros)
      if (vacio) return problema(422, 'sin-registros', 'No hay registros en ese periodo.')
      return new HttpResponse(new Blob(['PK…']), {
        headers: {
          'Content-Type': 'application/zip',
          'Content-Disposition': `attachment; filename="registros-${parametros.get('tipo') ?? ''}-x.zip"`,
        },
      })
    }),
  )
  return peticiones
}

describe('Registro fiscal → Exportar (004, FR-022)', () => {
  const clic = vi.fn()
  beforeEach(() => {
    URL.createObjectURL = vi.fn(() => 'blob:exportacion')
    URL.revokeObjectURL = vi.fn()
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(clic)
  })
  afterEach(() => {
    vi.restoreAllMocks()
    clic.mockReset()
  })

  it('propone el mes en curso y descarga el ZIP de facturación', async () => {
    conSesion(admin)
    const peticiones = conExportacion()
    renderApp('/registro-fiscal?pestana=exportar')
    const user = userEvent.setup()
    const hoy = claveDia(new Date())

    await user.click(await screen.findByRole('button', { name: 'Exportar' }))

    expect(await screen.findByText('Descargado registros-facturacion-x.zip.')).toBeInTheDocument()
    expect(peticiones.map((p) => Object.fromEntries(p))).toEqual([
      { tipo: 'facturacion', desde: `${hoy.slice(0, 8)}01`, hasta: hoy },
    ])
    expect(clic).toHaveBeenCalledOnce()
  })

  it('exporta los registros de evento si se eligen', async () => {
    conSesion(admin)
    const peticiones = conExportacion()
    renderApp('/registro-fiscal?pestana=exportar')
    const user = userEvent.setup()

    await user.click(await screen.findByRole('radio', { name: 'Registros de evento' }))
    await user.click(screen.getByRole('button', { name: 'Exportar' }))

    expect(await screen.findByText('Descargado registros-eventos-x.zip.')).toBeInTheDocument()
    expect(peticiones[0]?.get('tipo')).toBe('eventos')
  })

  it('un periodo sin registros lo avisa sin descargar nada', async () => {
    conSesion(admin)
    conExportacion(true)
    renderApp('/registro-fiscal?pestana=exportar')
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Exportar' }))

    expect(await screen.findByText('No hay registros en ese periodo.')).toBeInTheDocument()
    expect(clic).not.toHaveBeenCalled()
  })

  it('«desde» posterior a «hasta» es un error en el campo y no se pide nada', async () => {
    conSesion(admin)
    const peticiones = conExportacion()
    renderApp('/registro-fiscal?pestana=exportar')

    const desde = await screen.findByLabelText(/^Desde/)
    fireEvent.change(desde, { target: { value: '2099-01-01' } })

    expect(await screen.findByText('No puede ser anterior a «desde».')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Exportar' })).toBeDisabled()
    expect(peticiones).toEqual([])
  })
})
