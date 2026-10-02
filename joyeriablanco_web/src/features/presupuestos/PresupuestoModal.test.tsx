import { screen, within } from '@testing-library/react'
import userEvent, { type UserEvent } from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { conCatalogos, conSesion, crearCliente, crearSesion, renderApp } from '../../test/app'
import { server } from '../../test/msw'
import { conPresupuestos, crearPresupuesto, PARAMETROS_PRESUPUESTO } from '../../test/presupuestos'

const maria = crearCliente({ direccion: 'Calle Serrano, 45', localidad: 'Madrid' })
const sinDomicilio = crearCliente({
  id: '0192f0c0-0000-7000-8000-00000000c002',
  nombre: 'Pedro Sin Casa',
  direccion: null,
  codigo_postal: null,
  localidad: null,
})

interface Envio {
  cuerpo: Record<string, unknown>
  clave: string | null
}

function conEmision(cliente = maria, respuesta?: () => Response) {
  const envios: Envio[] = []
  const borradores: Record<string, unknown>[] = []
  server.use(
    http.get('*/api/v1/clientes', () =>
      HttpResponse.json({ elementos: [cliente], total: 1, pagina: 1, tamano: 25 }),
    ),
    http.get('*/api/v1/clientes/:id', () => HttpResponse.json(cliente)),
    http.post('*/api/v1/presupuestos', async ({ request }) => {
      envios.push({
        cuerpo: (await request.json()) as Record<string, unknown>,
        clave: request.headers.get('Idempotency-Key'),
      })
      return respuesta
        ? respuesta()
        : HttpResponse.json(crearPresupuesto({ num_serie: 'PRE-2026-0004' }), { status: 201 })
    }),
    http.post('*/api/v1/borradores-presupuesto', async ({ request }) => {
      borradores.push((await request.json()) as Record<string, unknown>)
      return HttpResponse.json({ id: 'b1' }, { status: 201 })
    }),
  )
  return { envios, borradores }
}

async function modalListo() {
  await screen.findByText('Se asigna al emitir')
  return screen.getByRole('dialog', { name: 'Nuevo presupuesto' })
}

async function elegirCliente(user: UserEvent, nombre = /María López García/) {
  await modalListo()
  await user.type(screen.getByRole('combobox', { name: /Cliente/ }), 'a')
  await user.click(await screen.findByRole('option', { name: nombre }))
}

async function escribirLinea(user: UserEvent) {
  await user.type(screen.getByRole('textbox', { name: 'Descripción de la línea 1' }), 'Anillo')
  await user.type(
    screen.getByRole('textbox', { name: 'Precio unitario sin IVA de la línea 1' }),
    '1.200',
  )
}

async function emitir(user: UserEvent) {
  await user.click(screen.getByRole('button', { name: 'Emitir presupuesto' }))
  const confirmacion = await screen.findByRole('alertdialog', { name: '¿Emitir el presupuesto?' })
  await user.click(within(confirmacion).getByRole('button', { name: 'Emitir presupuesto' }))
}

describe('Modal «Nuevo presupuesto» (005, US1)', () => {
  beforeEach(() => {
    conCatalogos()
  })

  it('tiene sus secciones, el número se asigna al emitir y propone la validez (FR-009)', async () => {
    conSesion(crearSesion())
    conPresupuestos()
    renderApp('/presupuestos/nuevo')

    const modal = await modalListo()
    expect(
      within(modal).getByRole('heading', { name: 'Datos del presupuesto' }),
    ).toBeInTheDocument()
    expect(
      within(modal).getByRole('heading', { name: 'Detalle del presupuesto' }),
    ).toBeInTheDocument()
    expect(within(modal).getByText('PRE-2026-0004')).toBeInTheDocument()
    expect(within(modal).getByLabelText(/^Fecha/)).toHaveValue(PARAMETROS_PRESUPUESTO.hoy)
    expect(within(modal).getByLabelText(/Válido hasta/)).toHaveValue('2026-10-29')
    expect(within(modal).getByText('Total presupuesto')).toBeInTheDocument()
  })

  it('al cambiar la fecha sin tocar la validez, la validez se recalcula (FR-009)', async () => {
    conSesion(crearSesion())
    conPresupuestos()
    renderApp('/presupuestos/nuevo')
    const user = userEvent.setup()

    const modal = await modalListo()
    const fecha = within(modal).getByLabelText(/^Fecha/)
    await user.clear(fecha)
    await user.type(fecha, '2026-09-01')

    expect(within(modal).getByLabelText(/Válido hasta/)).toHaveValue('2026-10-01')
  })

  it('emite con confirmación, la clave de operación y sin totales (FR-007, FR-014)', async () => {
    conSesion(crearSesion())
    conPresupuestos()
    const { envios } = conEmision()
    renderApp('/presupuestos/nuevo')
    const user = userEvent.setup()

    await elegirCliente(user)
    await escribirLinea(user)
    await emitir(user)

    expect(await screen.findByText('Presupuesto PRE-2026-0004 emitido')).toBeInTheDocument()
    expect(envios).toHaveLength(1)
    const [envio] = envios
    expect(envio?.clave).toMatch(/^[0-9a-f-]{36}$/)
    expect(envio?.cuerpo).toEqual({
      fecha: '2026-09-29',
      valido_hasta: '2026-10-29',
      cliente_id: maria.id,
      lineas: [{ unidades: '1.00', descripcion: 'Anillo', precio_unitario: '1200.00' }],
      oro_inversion: false,
    })
  })

  it('una validez anterior a la fecha se marca en su campo y no se envía', async () => {
    conSesion(crearSesion())
    conPresupuestos()
    const { envios } = conEmision()
    renderApp('/presupuestos/nuevo')
    const user = userEvent.setup()

    await elegirCliente(user)
    await escribirLinea(user)
    const validez = screen.getByLabelText(/Válido hasta/)
    await user.clear(validez)
    await user.type(validez, '2026-09-01')
    await user.click(screen.getByRole('button', { name: 'Emitir presupuesto' }))

    expect(
      await screen.findByText('«Válido hasta» no puede ser anterior a la fecha.'),
    ).toBeInTheDocument()
    expect(envios).toHaveLength(0)
  })

  it('avisa de que la factura no se podrá emitir si al cliente le falta el domicilio', async () => {
    conSesion(crearSesion())
    conPresupuestos()
    conEmision(sinDomicilio)
    renderApp('/presupuestos/nuevo')
    const user = userEvent.setup()

    await elegirCliente(user, /Pedro Sin Casa/)

    expect(
      await screen.findByText(/el presupuesto se puede emitir, pero la factura convertida no/),
    ).toBeInTheDocument()
  })

  it('un error de validación del servidor va a su campo', async () => {
    conSesion(crearSesion())
    conPresupuestos()
    conEmision(maria, () =>
      HttpResponse.json(
        {
          type: '/problemas/validacion',
          title: 'Datos no válidos',
          status: 422,
          errores: [{ campo: 'fecha', mensaje: 'La fecha no puede ser posterior a hoy.' }],
        },
        { status: 422, headers: { 'Content-Type': 'application/problem+json' } },
      ),
    )
    renderApp('/presupuestos/nuevo')
    const user = userEvent.setup()

    await elegirCliente(user)
    await escribirLinea(user)
    await emitir(user)

    expect(await screen.findByText('La fecha no puede ser posterior a hoy.')).toBeInTheDocument()
  })

  it('«Guardar borrador» envía el borrador sin totales y pasa al modo borrador', async () => {
    conSesion(crearSesion())
    conPresupuestos()
    const { borradores } = conEmision()
    server.use(
      http.get('*/api/v1/borradores-presupuesto/b1', () =>
        HttpResponse.json({
          id: 'b1',
          version: 1,
          fecha: '2026-09-29',
          valido_hasta: '2026-10-29',
          cliente: null,
          lineas: [],
          oro_inversion: false,
          mencion_exencion: null,
          totales_previstos: {
            desglose: [{ tipo_iva: '21.00', base: '0.00', cuota: '0.00' }],
            base_total: '0.00',
            cuota_total: '0.00',
            importe_total: '0.00',
          },
          tipo_iva_previsto: '21.00',
          creado_en: '2026-09-29T08:00:00Z',
          creado_por: { id: 'u1', nombre: 'Ana García', eliminado: false },
          actualizado_en: '2026-09-29T08:00:00Z',
          actualizado_por: { id: 'u1', nombre: 'Ana García', eliminado: false },
        }),
      ),
    )
    renderApp('/presupuestos/nuevo')
    const user = userEvent.setup()

    await modalListo()
    await user.click(screen.getByRole('button', { name: 'Quitar la línea 1' }))
    await user.click(screen.getByRole('button', { name: 'Guardar borrador' }))

    expect(
      await screen.findByRole('dialog', { name: 'Borrador de presupuesto' }),
    ).toBeInTheDocument()
    expect(borradores[0]).toMatchObject({ fecha: '2026-09-29', valido_hasta: '2026-10-29' })
    expect(Object.keys(borradores[0] ?? {})).not.toContain('importe_total')
    expect(screen.getByRole('button', { name: 'Eliminar borrador' })).toBeInTheDocument()
  })
})
