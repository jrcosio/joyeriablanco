import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import type { PresupuestoSalida } from '../../api/tipos'
import {
  conCatalogos,
  conSesion,
  crearCliente,
  crearSesion,
  problema,
  renderApp,
} from '../../test/app'
import { server } from '../../test/msw'
import { conPresupuestos, crearPresupuesto, PARAMETROS_PRESUPUESTO } from '../../test/presupuestos'

const admin = crearSesion({ rol: 'administrador', nombre: 'Luis Martín' })
const ID = '0192f0c0-0000-7000-8000-0000000e0003'
const ID_NUEVO = '0192f0c0-0000-7000-8000-0000000e0004'
const NUEVO = crearPresupuesto({
  id: ID_NUEVO,
  num_serie: 'PRE-2026-0004',
  sustituye_a: { id: ID, num_serie: 'PRE-2026-0003', fecha: '2026-09-29' },
})

interface Envio {
  cuerpo: unknown
  clave: string | null
}

/** El original, el nuevo y la modificación, con su respuesta. */
function conModificacion(
  original: PresupuestoSalida = crearPresupuesto(),
  respuesta: () => Response = () => HttpResponse.json(NUEVO, { status: 201 }),
) {
  const envios: Envio[] = []
  const maria = crearCliente()
  server.use(
    http.get('*/api/v1/clientes', () =>
      HttpResponse.json({ elementos: [maria], total: 1, pagina: 1, tamano: 25 }),
    ),
    http.get('*/api/v1/clientes/:id', () => HttpResponse.json(maria)),
    http.get(`*/api/v1/presupuestos/${ID}`, () => HttpResponse.json(original)),
    http.get(`*/api/v1/presupuestos/${ID_NUEVO}`, () => HttpResponse.json(NUEVO)),
    http.post(`*/api/v1/presupuestos/${ID}/modificacion`, async ({ request }) => {
      envios.push({ cuerpo: await request.json(), clave: request.headers.get('Idempotency-Key') })
      return respuesta()
    }),
  )
  return envios
}

async function abrir() {
  const app = renderApp(`/presupuestos/${ID}/modificar`)
  const modal = await screen.findByRole('dialog', { name: 'Modificar presupuesto PRE-2026-0003' })
  return { ...app, modal, user: userEvent.setup() }
}

describe('Modificar un presupuesto emitido (005, US4)', () => {
  beforeEach(() => {
    conSesion(admin)
    conCatalogos()
    conPresupuestos()
  })

  it('se abre con sus datos, la fecha de hoy y su validez', async () => {
    conModificacion()
    const { modal } = await abrir()

    expect(within(modal).getByLabelText(/^Fecha/)).toHaveValue(PARAMETROS_PRESUPUESTO.hoy)
    expect(within(modal).getByLabelText(/Válido hasta/)).toHaveValue('2026-10-29')
    expect(within(modal).getByRole('textbox', { name: 'Descripción de la línea 1' })).toHaveValue(
      'Anillo',
    )
    expect(
      within(modal).getByRole('textbox', { name: 'Precio unitario sin IVA de la línea 1' }),
    ).toHaveValue('1.200,00')
    expect(within(modal).getByDisplayValue(/María López García/)).toBeInTheDocument()
  })

  it('si la validez del original ya pasó, propone hoy más la validez por defecto (FR-015)', async () => {
    conModificacion(
      crearPresupuesto({ estado: 'caducado', fecha: '2026-07-01', valido_hasta: '2026-07-31' }),
    )
    const { modal } = await abrir()

    // 29/09/2026 + 30 días
    expect(within(modal).getByLabelText(/Válido hasta/)).toHaveValue('2026-10-29')
  })

  it('pide un motivo obligatorio, envía con la clave y abre el nuevo con el aviso', async () => {
    const envios = conModificacion()
    const { modal, user, router } = await abrir()
    const precio = within(modal).getByRole('textbox', {
      name: 'Precio unitario sin IVA de la línea 1',
    })
    await user.clear(precio)
    await user.type(precio, '1.100')
    await user.click(within(modal).getByRole('button', { name: 'Guardar' }))

    const motivo = await screen.findByRole('alertdialog', { name: '¿Sustituir PRE-2026-0003?' })
    await user.click(within(motivo).getByRole('button', { name: 'Emitir el nuevo' }))
    expect(within(motivo).getByText('Campo obligatorio.')).toBeInTheDocument()
    expect(envios).toEqual([])
    await user.type(within(motivo).getByRole('textbox', { name: /Motivo/ }), 'Cambio de precio')
    await user.click(within(motivo).getByRole('button', { name: 'Emitir el nuevo' }))

    expect(
      await screen.findByText('Se ha emitido PRE-2026-0004. PRE-2026-0003 queda sustituido'),
    ).toBeInTheDocument()
    expect(envios.map((e) => e.cuerpo)).toEqual([
      {
        fecha: PARAMETROS_PRESUPUESTO.hoy,
        valido_hasta: '2026-10-29',
        cliente_id: crearCliente().id,
        lineas: [
          { unidades: '1.00', descripcion: 'Anillo', precio_unitario: '1100.00' },
          { unidades: '2.00', descripcion: 'Ajuste', precio_unitario: '45.00' },
        ],
        oro_inversion: false,
        motivo_texto: 'Cambio de precio',
      },
    ])
    expect(envios[0]?.clave).toMatch(/^[0-9a-f-]{36}$/)
    await waitFor(() => {
      expect(router.state.location.pathname).toBe(`/presupuestos/${ID_NUEVO}`)
    })
    const consulta = await screen.findByRole('dialog', { name: 'Presupuesto PRE-2026-0004' })
    expect(within(consulta).getByText(/Sustituye a/)).toBeInTheDocument()
  })

  it('sin cambios, lo explica y sigue en el modal', async () => {
    conModificacion(crearPresupuesto(), () =>
      problema(
        422,
        'sin-cambios',
        'El presupuesto nuevo sería idéntico al original: cambia algún dato además de la fecha.',
      ),
    )
    const { modal, user } = await abrir()

    await user.click(within(modal).getByRole('button', { name: 'Guardar' }))
    const motivo = await screen.findByRole('alertdialog', { name: '¿Sustituir PRE-2026-0003?' })
    await user.type(within(motivo).getByRole('textbox', { name: /Motivo/ }), 'Nada')
    await user.click(within(motivo).getByRole('button', { name: 'Emitir el nuevo' }))

    expect(await within(modal).findByRole('alert')).toHaveTextContent(
      'cambia algún dato además de la fecha',
    )
    expect(
      screen.getByRole('dialog', { name: 'Modificar presupuesto PRE-2026-0003' }),
    ).toBeInTheDocument()
  })

  it('uno en facturación o cerrado no se modifica', async () => {
    conModificacion(crearPresupuesto({ estado: 'en_facturacion', borrador_factura: { id: 'b1' } }))
    const { modal } = await abrir()

    expect(
      within(modal).getByText(/Solo se puede modificar un presupuesto pendiente/),
    ).toBeVisible()
    expect(within(modal).queryByRole('button', { name: 'Guardar' })).toBeNull()
  })

  it('un empleado no puede abrir «Modificar»', async () => {
    conSesion(crearSesion({ rol: 'empleado' }))
    conModificacion()
    renderApp(`/presupuestos/${ID}/modificar`)

    expect(await screen.findByRole('heading', { name: 'Acceso denegado' })).toBeInTheDocument()
    expect(screen.queryByRole('dialog', { name: 'Modificar presupuesto PRE-2026-0003' })).toBeNull()
  })
})
