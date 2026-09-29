import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import type { FacturaSalida } from '../../api/tipos'
import {
  conCatalogos,
  conSesion,
  crearCliente,
  crearSesion,
  problema,
  renderApp,
} from '../../test/app'
import { conFacturacion, crearFactura, PARAMETROS } from '../../test/facturas'
import { server } from '../../test/msw'

const admin = crearSesion({ rol: 'administrador', nombre: 'Luis Martín' })
const ID = '0192f0c0-0000-7000-8000-0000000f0001'
const ID_REC = '0192f0c0-0000-7000-8000-0000000f0009'

interface Peticion {
  ruta: string
  cuerpo: unknown
  clave: string | null
}

/**
 * El detalle devuelve `antes`, y `despues` una vez anulada; `otras` son más facturas por id. Se
 * registran las acciones.
 */
function conFactura(
  [antes, despues = antes]: [FacturaSalida, FacturaSalida?],
  otras: Record<string, FacturaSalida> = {},
) {
  const peticiones: Peticion[] = []
  let anulada = false
  const maria = crearCliente()
  server.use(
    http.get('*/api/v1/clientes', () =>
      HttpResponse.json({ elementos: [maria], total: 1, pagina: 1, tamano: 25 }),
    ),
    http.get('*/api/v1/clientes/:id', () => HttpResponse.json(maria)),
    http.get('*/api/v1/facturas/:id', ({ params }) => {
      const id = String(params.id)
      if (id === 'parametros') return undefined // lo atiende `conFacturacion`
      if (id in otras) return HttpResponse.json(otras[id])
      return HttpResponse.json(anulada ? despues : antes)
    }),
    http.post('*/api/v1/facturas/:id/anulacion', async ({ request, params }) => {
      peticiones.push({
        ruta: `anulacion:${String(params.id)}`,
        cuerpo: await request.json(),
        clave: request.headers.get('Idempotency-Key'),
      })
      anulada = true
      return HttpResponse.json(despues)
    }),
    http.post('*/api/v1/facturas/:id/modificacion', async ({ request, params }) => {
      peticiones.push({
        ruta: `modificacion:${String(params.id)}`,
        cuerpo: await request.json(),
        clave: request.headers.get('Idempotency-Key'),
      })
      return HttpResponse.json(otras[ID_REC], { status: 201 })
    }),
  )
  return peticiones
}

const anulada = crearFactura({
  estado: 'anulada',
  vigente_actual: { id: 'f2', num_serie: 'FAC-2026-0012' },
  correcciones: [
    {
      tipo: 'anulacion_y_reemision',
      motivo: 'no_debio_emitirse',
      motivo_texto: 'Número equivocado',
      creada_en: '2026-09-29T09:00:00Z',
      creada_por: { id: 'u2', nombre: 'Luis Martín', eliminado: false },
      factura_nueva: { id: 'f2', num_serie: 'FAC-2026-0012' },
      en_vigor: true,
    },
  ],
})

const rectificativa = crearFactura({
  id: ID_REC,
  num_serie: 'REC-2026-0001',
  tipo_factura: 'R4',
  tipo_rectificativa: 'S',
  rectifica_a: {
    factura: { id: ID, num_serie: 'FAC-2026-0005' },
    base_rectificada: '1290.00',
    cuota_rectificada: '270.90',
    causa: 'error_datos',
  },
})

describe('Consulta de una factura emitida (US5)', () => {
  beforeEach(() => {
    conCatalogos()
    conFacturacion()
  })

  it('un empleado solo puede cerrarla', async () => {
    conSesion(crearSesion({ rol: 'empleado' }))
    conFactura([crearFactura()])
    renderApp(`/facturas/${ID}`)

    const modal = await screen.findByRole('dialog', { name: 'Factura FAC-2026-0005' })
    expect(within(modal).getByRole('button', { name: 'Cerrar' })).toBeInTheDocument()
    expect(within(modal).queryByRole('button', { name: 'Anular' })).toBeNull()
    expect(within(modal).queryByRole('link', { name: 'Modificar' })).toBeNull()
  })

  it('un administrador puede anular o modificar la vigente', async () => {
    conSesion(admin)
    conFactura([crearFactura()])
    renderApp(`/facturas/${ID}`)

    const modal = await screen.findByRole('dialog', { name: 'Factura FAC-2026-0005' })
    expect(within(modal).getByRole('button', { name: 'Anular' })).toBeInTheDocument()
    expect(within(modal).getByRole('link', { name: 'Modificar' })).toHaveAttribute(
      'href',
      expect.stringMatching(new RegExp(`^/facturas/${ID}/modificar`)),
    )
  })

  it('una anulada muestra la marca, el enlace a la vigente y el historial, sin acciones', async () => {
    conSesion(admin)
    conFactura([anulada])
    renderApp(`/facturas/${ID}`)
    const user = userEvent.setup()

    const modal = await screen.findByRole('dialog', { name: 'Factura FAC-2026-0005' })
    expect(within(modal).getByText('Anulada')).toBeInTheDocument()
    expect(within(modal).getByText(/La factura vigente es/)).toBeInTheDocument()
    expect(within(modal).getAllByRole('link', { name: 'FAC-2026-0012' })[0]).toHaveAttribute(
      'href',
      expect.stringMatching(/^\/facturas\/f2/),
    )
    expect(within(modal).queryByRole('button', { name: 'Anular' })).toBeNull()
    expect(within(modal).queryByRole('link', { name: 'Modificar' })).toBeNull()

    const historial = within(modal).getByRole('button', { name: 'Historial' })
    expect(historial).toHaveAttribute('aria-expanded', 'true')
    expect(within(modal).getByText('Anulación y reemisión')).toBeInTheDocument()
    expect(within(modal).getByText(/Número equivocado/)).toBeInTheDocument()
    expect(within(modal).getByText(/Luis Martín/)).toBeInTheDocument()
    expect(within(modal).getByText(/Registro de alta nº 5/)).toBeInTheDocument()
    await user.click(historial)
    expect(historial).toHaveAttribute('aria-expanded', 'false')
    expect(within(modal).queryByText('Anulación y reemisión')).not.toBeVisible()
  })

  it('una rectificativa enseña su causa, lo rectificado y a qué factura rectifica', async () => {
    conSesion(admin)
    conFactura([rectificativa])
    renderApp(`/facturas/${ID_REC}`)

    const modal = await screen.findByRole('dialog', { name: 'Factura REC-2026-0001' })
    expect(within(modal).getByText('Rectificativa R4')).toBeInTheDocument()
    expect(within(modal).getByText('Error en datos o importes de la factura')).toBeInTheDocument()
    expect(within(modal).getByText(/Rectifica a/)).toBeInTheDocument()
    expect(within(modal).getByRole('link', { name: 'FAC-2026-0005' })).toBeInTheDocument()
  })

  it('anular pide la declaración, envía la clave y deja la factura ya anulada', async () => {
    conSesion(admin)
    const peticiones = conFactura([crearFactura(), crearFactura({ estado: 'anulada' })])
    renderApp(`/facturas/${ID}`)
    const user = userEvent.setup()

    const modal = await screen.findByRole('dialog', { name: 'Factura FAC-2026-0005' })
    await user.click(within(modal).getByRole('button', { name: 'Anular' }))
    const dialogo = await screen.findByRole('alertdialog', {
      name: '¿Anular la factura FAC-2026-0005?',
    })
    await user.click(within(dialogo).getByRole('checkbox'))
    await user.type(within(dialogo).getByRole('textbox', { name: /Motivo/ }), 'Duplicada')
    await user.click(within(dialogo).getByRole('button', { name: 'Anular factura' }))

    expect(await screen.findByText('Factura FAC-2026-0005 anulada')).toBeInTheDocument()
    expect(peticiones.map(({ ruta, cuerpo }) => ({ ruta, cuerpo }))).toEqual([
      {
        ruta: `anulacion:${ID}`,
        cuerpo: { declaracion_no_debio_emitirse: true, motivo_texto: 'Duplicada' },
      },
    ])
    expect(peticiones[0]?.clave).toMatch(/^[0-9a-f-]{36}$/)
    expect(await within(modal).findByText('Anulada')).toBeInTheDocument()
    expect(within(modal).queryByRole('button', { name: 'Anular' })).toBeNull()
  })
})

describe('Modificar una factura emitida (US5)', () => {
  beforeEach(() => {
    conCatalogos()
    conFacturacion()
  })

  it('pide el motivo y, tras guardar, muestra la factura nueva con el aviso de FR-049', async () => {
    conSesion(admin)
    const peticiones = conFactura([crearFactura()], { [ID_REC]: rectificativa })
    const { router } = renderApp(`/facturas/${ID}/modificar`)
    const user = userEvent.setup()

    const modal = await screen.findByRole('dialog', { name: 'Modificar factura FAC-2026-0005' })
    expect(within(modal).getByText(/Fecha de la operación: 29\/09\/2026/)).toBeInTheDocument()
    const precio = within(modal).getByRole('textbox', {
      name: 'Precio unitario sin IVA de la línea 1',
    })
    expect(precio).toHaveValue('1.200,00')
    await user.clear(precio)
    await user.type(precio, '1.100')
    await user.click(within(modal).getByRole('button', { name: 'Guardar' }))

    const motivo = await screen.findByRole('alertdialog', { name: 'Motivo de la modificación' })
    await user.click(within(motivo).getByRole('radio', { name: /ya entregada/ }))
    await user.click(within(motivo).getByRole('radio', { name: /Error en datos/ }))
    await user.type(within(motivo).getByRole('textbox', { name: /Explica el motivo/ }), 'Precio')
    await user.click(within(motivo).getByRole('button', { name: 'Confirmar' }))

    expect(
      await screen.findByText('Se ha emitido REC-2026-0001. FAC-2026-0005 queda rectificada'),
    ).toBeInTheDocument()
    expect(peticiones.map(({ ruta, cuerpo }) => ({ ruta, cuerpo }))).toEqual([
      {
        ruta: `modificacion:${ID}`,
        cuerpo: {
          motivo: 'factura_entregada',
          causa: 'error_datos',
          motivo_texto: 'Precio',
          cliente_id: crearCliente().id,
          fecha_expedicion: PARAMETROS.hoy, // propone la de hoy (FR-018)
          lineas: [
            { unidades: '1.00', descripcion: 'Anillo', precio_unitario: '1100.00' },
            { unidades: '2.00', descripcion: 'Ajuste', precio_unitario: '45.00' },
          ],
        },
      },
    ])
    expect(peticiones[0]?.clave).toMatch(/^[0-9a-f-]{36}$/)
    await waitFor(() => {
      expect(router.state.location.pathname).toBe(`/facturas/${ID_REC}`)
    })
    expect(await screen.findByRole('dialog', { name: 'Factura REC-2026-0001' })).toBeVisible()
  })

  it('la fecha es editable y no admite una anterior a la de la operación (FR-018)', async () => {
    conSesion(admin)
    const original = crearFactura({ fecha_expedicion: '2026-09-10', fecha_operacion: '2026-09-08' })
    conFactura([original])
    server.use(
      http.post('*/api/v1/facturas/:id/modificacion', () =>
        problema(
          422,
          'fecha-expedicion',
          'La fecha de expedición no puede ser anterior a la de la operación (08/09/2026).',
        ),
      ),
    )
    renderApp(`/facturas/${ID}/modificar`)
    const user = userEvent.setup()

    const modal = await screen.findByRole('dialog', { name: 'Modificar factura FAC-2026-0005' })
    const fecha = within(modal).getByLabelText(/^Fecha/)
    expect(fecha).toHaveValue(PARAMETROS.hoy)
    expect(fecha).toHaveAttribute('min', '2026-09-08')
    expect(fecha).toHaveAttribute('max', PARAMETROS.hoy)
    expect(within(modal).getByText(/Fecha de la operación: 08\/09\/2026/)).toBeInTheDocument()

    await user.click(within(modal).getByRole('button', { name: 'Guardar' }))
    const motivo = await screen.findByRole('alertdialog', { name: 'Motivo de la modificación' })
    await user.click(within(motivo).getByRole('radio', { name: /no debió emitirse/ }))
    await user.type(within(motivo).getByRole('textbox', { name: /Explica el motivo/ }), 'Número')
    await user.click(within(motivo).getByRole('button', { name: 'Confirmar' }))

    expect(
      await within(modal).findByText(/no puede ser anterior a la de la operación/),
    ).toBeInTheDocument()
    expect(fecha).toHaveAttribute('aria-invalid', 'true')
  })

  it('un empleado no puede abrir «Modificar»', async () => {
    conSesion(crearSesion({ rol: 'empleado' }))
    conFactura([crearFactura()])
    renderApp(`/facturas/${ID}/modificar`)

    expect(await screen.findByRole('heading', { name: 'Acceso denegado' })).toBeInTheDocument()
  })

  it('una factura que ya no está vigente no se modifica', async () => {
    conSesion(admin)
    conFactura([anulada])
    renderApp(`/facturas/${ID}/modificar`)

    expect(await screen.findByText(/Solo se puede modificar la factura vigente/)).toBeVisible()
    expect(screen.getByRole('link', { name: 'Ver FAC-2026-0012' })).toBeInTheDocument()
  })
})
