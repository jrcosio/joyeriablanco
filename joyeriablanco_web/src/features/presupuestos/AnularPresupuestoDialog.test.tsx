import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { conSesion, crearSesion, renderApp } from '../../test/app'
import { server } from '../../test/msw'
import { conPresupuestos, crearPresupuesto } from '../../test/presupuestos'

const ID = '0192f0c0-0000-7000-8000-0000000e0003'
const ANULADO = crearPresupuesto({
  estado: 'anulado',
  cierre: {
    tipo: 'anulacion',
    motivo_texto: 'Rechazado por el cliente',
    creado_en: '2026-09-30T10:00:00Z',
    creado_por: { id: 'u2', nombre: 'Luis Martín', eliminado: false },
    presupuesto_nuevo: null,
    factura: null,
    factura_vigente: null,
  },
})

/** La consulta devuelve el pendiente y, una vez anulado, el anulado. Se registran los envíos. */
function conAnulacion() {
  const envios: { cuerpo: unknown; clave: string | null }[] = []
  server.use(
    http.get(`*/api/v1/presupuestos/${ID}`, () =>
      HttpResponse.json(envios.length ? ANULADO : crearPresupuesto()),
    ),
    http.post(`*/api/v1/presupuestos/${ID}/anulacion`, async ({ request }) => {
      envios.push({ cuerpo: await request.json(), clave: request.headers.get('Idempotency-Key') })
      return HttpResponse.json(ANULADO)
    }),
  )
  return envios
}

describe('Anular un presupuesto (005, US4)', () => {
  beforeEach(() => {
    conSesion(crearSesion({ rol: 'administrador' }))
    conPresupuestos()
  })

  it('pide el motivo, envía la clave y deja el presupuesto anulado en la consulta', async () => {
    const envios = conAnulacion()
    renderApp(`/presupuestos/${ID}`)
    const user = userEvent.setup()
    const modal = await screen.findByRole('dialog', { name: 'Presupuesto PRE-2026-0003' })

    await user.click(within(modal).getByRole('button', { name: 'Anular' }))
    const dialogo = await screen.findByRole('alertdialog', {
      name: '¿Anular el presupuesto PRE-2026-0003?',
    })
    await user.click(within(dialogo).getByRole('button', { name: 'Anular presupuesto' }))
    expect(within(dialogo).getByText('Campo obligatorio.')).toBeInTheDocument()
    expect(envios).toEqual([])

    await user.type(
      within(dialogo).getByRole('textbox', { name: /Motivo/ }),
      '  Rechazado por el cliente ',
    )
    await user.click(within(dialogo).getByRole('button', { name: 'Anular presupuesto' }))

    expect(await screen.findByText('Presupuesto PRE-2026-0003 anulado')).toBeInTheDocument()
    expect(envios.map((e) => e.cuerpo)).toEqual([{ motivo_texto: 'Rechazado por el cliente' }])
    expect(envios[0]?.clave).toMatch(/^[0-9a-f-]{36}$/)
    expect(await within(modal).findAllByText('Anulado')).toHaveLength(2) // marca e historial
    expect(within(modal).getByText('Rechazado por el cliente')).toBeInTheDocument()
    for (const accion of ['Anular', 'Convertir en factura']) {
      expect(within(modal).queryByRole('button', { name: accion })).toBeNull()
    }
    expect(within(modal).queryByRole('link', { name: 'Modificar' })).toBeNull()
  })

  it('un empleado no ve «Anular» ni «Modificar», pero sí puede convertir', async () => {
    conSesion(crearSesion({ rol: 'empleado' }))
    conAnulacion()
    renderApp(`/presupuestos/${ID}`)

    const modal = await screen.findByRole('dialog', { name: 'Presupuesto PRE-2026-0003' })
    expect(within(modal).queryByRole('button', { name: 'Anular' })).toBeNull()
    expect(within(modal).queryByRole('link', { name: 'Modificar' })).toBeNull()
    expect(within(modal).getByRole('button', { name: 'Convertir en factura' })).toBeInTheDocument()
  })

  it('un administrador ve «Modificar», que abre su modal', async () => {
    conAnulacion()
    renderApp(`/presupuestos/${ID}`)

    const modal = await screen.findByRole('dialog', { name: 'Presupuesto PRE-2026-0003' })
    expect(within(modal).getByRole('link', { name: 'Modificar' })).toHaveAttribute(
      'href',
      expect.stringMatching(new RegExp(`^/presupuestos/${ID}/modificar(\\?|$)`)),
    )
  })
})
