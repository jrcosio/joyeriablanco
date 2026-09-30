import { screen, waitFor, within } from '@testing-library/react'
import userEvent, { type UserEvent } from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import type { BorradorSalida } from '../../api/tipos'
import {
  conCatalogos,
  conSesion,
  crearCliente,
  crearSesion,
  problema,
  renderApp,
} from '../../test/app'
import { conFacturacion, crearFactura, MENCION_ORO, PARAMETROS } from '../../test/facturas'
import { server } from '../../test/msw'

const ID = '0192f0c0-0000-7000-8000-0000000b0001'
const maria = crearCliente({ direccion: 'Calle Serrano, 45' })

function crearBorrador(parcial: Partial<BorradorSalida> = {}): BorradorSalida {
  return {
    id: ID,
    version: 3,
    fecha_expedicion: '2026-09-28',
    cliente: {
      id: maria.id,
      nombre: 'María López García',
      identificacion_pais: 'ES',
      identificacion_tipo: 'NIF',
      identificacion_numero: '12345678Z',
      direccion: 'Calle Serrano, 45',
      codigo_postal: '29005',
      localidad: 'Málaga',
      provincia: 'Málaga',
      pais: 'ES',
      activo: true,
    },
    lineas: [
      {
        orden: 1,
        unidades: '1.00',
        descripcion: 'Anillo',
        precio_unitario: '1200.00',
        importe: '1200.00',
      },
    ],
    totales_previstos: {
      desglose: [{ tipo_iva: '21.00', base: '1200.00', cuota: '252.00' }],
      base_total: '1200.00',
      cuota_total: '252.00',
      importe_total: '1452.00',
    },
    tipo_iva_previsto: '21.00',
    oro_inversion: false,
    mencion_exencion: null,
    creado_en: '2026-09-28T08:00:00Z',
    creado_por: { id: 'u1', nombre: 'Ana García', eliminado: false },
    actualizado_en: '2026-09-28T08:00:00Z',
    actualizado_por: { id: 'u1', nombre: 'Ana García', eliminado: false },
    ...parcial,
  }
}

interface Peticion {
  metodo: string
  cuerpo: unknown
  clave: string | null
}

/** La API del borrador: cada lectura devuelve el siguiente de `lecturas` (el último se repite). */
function conBorrador(
  lecturas: (() => Response)[],
  respuestas: Partial<Record<'PUT' | 'DELETE' | 'EMISION', () => Response>> = {},
) {
  const peticiones: Peticion[] = []
  let leidas = 0
  server.use(
    http.get('*/api/v1/clientes', () =>
      HttpResponse.json({ elementos: [maria], total: 1, pagina: 1, tamano: 25 }),
    ),
    http.get('*/api/v1/clientes/:id', () => HttpResponse.json(maria)),
    http.get(`*/api/v1/borradores-factura/${ID}`, () => {
      const lectura = lecturas[Math.min(leidas, lecturas.length - 1)]
      leidas += 1
      return lectura ? lectura() : HttpResponse.json(crearBorrador())
    }),
    http.put(`*/api/v1/borradores-factura/${ID}`, async ({ request }) => {
      peticiones.push({ metodo: 'PUT', cuerpo: await request.json(), clave: null })
      return respuestas.PUT ? respuestas.PUT() : HttpResponse.json(crearBorrador({ version: 4 }))
    }),
    http.delete(`*/api/v1/borradores-factura/${ID}`, () => {
      peticiones.push({ metodo: 'DELETE', cuerpo: null, clave: null })
      return respuestas.DELETE ? respuestas.DELETE() : new HttpResponse(null, { status: 204 })
    }),
    http.post(`*/api/v1/borradores-factura/${ID}/emision`, async ({ request }) => {
      peticiones.push({
        metodo: 'EMISION',
        cuerpo: await request.json(),
        clave: request.headers.get('Idempotency-Key'),
      })
      return respuestas.EMISION
        ? respuestas.EMISION()
        : HttpResponse.json(crearFactura({ num_serie: 'FAC-2026-0006' }), { status: 201 })
    }),
  )
  return peticiones
}

async function abrir(): Promise<{
  user: UserEvent
  router: ReturnType<typeof renderApp>['router']
}> {
  const { router } = renderApp(`/facturas/borradores/${ID}`)
  await screen.findByText('Se asigna al emitir')
  return { user: userEvent.setup(), router }
}

describe('Modal en modo borrador (US4)', () => {
  beforeEach(() => {
    conSesion(crearSesion())
    conCatalogos()
    conFacturacion()
  })

  it('abre el borrador con sus datos y los cuatro botones', async () => {
    conBorrador([() => HttpResponse.json(crearBorrador())])
    await abrir()

    const modal = screen.getByRole('dialog', { name: 'Borrador' })
    for (const nombre of ['Cancelar', 'Eliminar borrador', 'Guardar borrador', 'Emitir factura']) {
      expect(within(modal).getByRole('button', { name: nombre })).toBeInTheDocument()
    }
    expect(within(modal).getByLabelText(/Fecha/)).toHaveValue('2026-09-28')
    expect(within(modal).getByRole('combobox', { name: /Cliente/ })).toHaveValue(
      'María López García · 12345678Z',
    )
    expect(within(modal).getByRole('textbox', { name: 'Descripción de la línea 1' })).toHaveValue(
      'Anillo',
    )
    expect(
      within(modal).getByRole('textbox', { name: 'Precio unitario sin IVA de la línea 1' }),
    ).toHaveValue('1.200,00')
    expect(screen.queryByText(/El IVA por defecto ha cambiado/)).not.toBeInTheDocument()
  })

  it('guarda con su versión, sin totales, y la siguiente vez usa la nueva', async () => {
    const peticiones = conBorrador([() => HttpResponse.json(crearBorrador())])
    const { user } = await abrir()

    await user.type(screen.getByRole('textbox', { name: 'Descripción de la línea 1' }), ' oro')
    await user.click(screen.getByRole('button', { name: 'Guardar borrador' }))
    expect(await screen.findByText('Borrador guardado')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Guardar borrador' }))

    await waitFor(() => {
      expect(peticiones.filter((p) => p.metodo === 'PUT')).toHaveLength(2)
    })
    expect(peticiones[0]?.cuerpo).toEqual({
      fecha_expedicion: '2026-09-28',
      cliente_id: maria.id,
      lineas: [{ unidades: '1.00', descripcion: 'Anillo oro', precio_unitario: '1200.00' }],
      oro_inversion: false,
      version: 3,
    })
    expect((peticiones[1]?.cuerpo as { version: number }).version).toBe(4)
  })

  it('ante un conflicto de versión ofrece recargar los datos actuales', async () => {
    conBorrador(
      [
        () => HttpResponse.json(crearBorrador()),
        () =>
          HttpResponse.json(
            crearBorrador({
              version: 5,
              lineas: [
                {
                  orden: 1,
                  unidades: '2.00',
                  descripcion: 'Collar',
                  precio_unitario: '300.00',
                  importe: '600.00',
                },
              ],
            }),
          ),
      ],
      { PUT: () => problema(409, 'conflicto-version', 'El borrador ha cambiado.') },
    )
    const { user } = await abrir()

    await user.type(screen.getByRole('textbox', { name: 'Descripción de la línea 1' }), ' oro')
    await user.click(screen.getByRole('button', { name: 'Guardar borrador' }))
    const dialogo = await screen.findByRole('alertdialog', { name: 'El borrador ha cambiado' })
    await user.click(within(dialogo).getByRole('button', { name: 'Recargar datos' }))

    await waitFor(() => {
      expect(screen.getByRole('textbox', { name: 'Descripción de la línea 1' })).toHaveValue(
        'Collar',
      )
    })
    expect(screen.getByRole('textbox', { name: 'Unidades de la línea 1' })).toHaveValue('2,00')
  })

  it('si otro usuario ya lo emitió, lo dice y no emite nada', async () => {
    const peticiones = conBorrador([() => HttpResponse.json(crearBorrador())], {
      EMISION: () => problema(404, 'no-encontrado', 'Este borrador ya no existe.'),
    })
    const { user } = await abrir()

    await user.click(screen.getByRole('button', { name: 'Emitir factura' }))
    const confirmacion = await screen.findByRole('alertdialog', { name: '¿Emitir la factura?' })
    await user.click(within(confirmacion).getByRole('button', { name: 'Emitir factura' }))

    expect(await screen.findByText(/Este borrador ya se ha emitido/)).toBeInTheDocument()
    expect(peticiones.filter((p) => p.metodo === 'EMISION')).toHaveLength(1)
  })

  it('emite con la versión y la clave de operación, y vuelve al listado', async () => {
    const peticiones = conBorrador([() => HttpResponse.json(crearBorrador())])
    const { user, router } = await abrir()

    await user.click(screen.getByRole('button', { name: 'Emitir factura' }))
    const confirmacion = await screen.findByRole('alertdialog', { name: '¿Emitir la factura?' })
    await user.click(within(confirmacion).getByRole('button', { name: 'Emitir factura' }))

    expect(await screen.findByText('Factura FAC-2026-0006 emitida')).toBeInTheDocument()
    const [emision] = peticiones
    expect((emision?.cuerpo as { version: number }).version).toBe(3)
    expect(emision?.clave).toMatch(/^[0-9a-f-]{36}$/)
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/facturas')
    })
  })

  it('pide confirmación antes de eliminarlo y vuelve al listado', async () => {
    const peticiones = conBorrador([() => HttpResponse.json(crearBorrador())])
    const { user, router } = await abrir()

    await user.click(screen.getByRole('button', { name: 'Eliminar borrador' }))
    const dialogo = await screen.findByRole('alertdialog', { name: '¿Eliminar el borrador?' })
    expect(within(dialogo).getByText(/no consume ningún número/)).toBeInTheDocument()
    await user.click(within(dialogo).getByRole('button', { name: 'Eliminar borrador' }))

    expect(await screen.findByText('Borrador eliminado')).toBeInTheDocument()
    expect(peticiones.map((p) => p.metodo)).toEqual(['DELETE'])
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/facturas')
    })
  })

  it('avisa si el IVA cambió desde que se guardó', async () => {
    conBorrador([() => HttpResponse.json(crearBorrador({ tipo_iva_previsto: '10.00' }))])
    await abrir()

    expect(
      screen.getByText(/El IVA por defecto ha cambiado desde que se guardó este borrador/),
    ).toHaveTextContent('del 10 % al 21 %')
    expect(screen.getByText('IVA (21 %)')).toBeInTheDocument()
  })

  it('un borrador de oro de inversión se abre sin IVA ni aviso de cambio y lo guarda', async () => {
    const peticiones = conBorrador([
      () =>
        HttpResponse.json(
          crearBorrador({
            tipo_iva_previsto: '10.00',
            oro_inversion: true,
            mencion_exencion: MENCION_ORO,
            totales_previstos: {
              desglose: [{ tipo_iva: null, base: '1200.00', cuota: '0.00' }],
              base_total: '1200.00',
              cuota_total: '0.00',
              importe_total: '1200.00',
            },
          }),
        ),
    ])
    const { user } = await abrir()

    expect(screen.getByRole('checkbox', { name: 'Sin IVA (oro de inversión)' })).toBeChecked()
    expect(screen.queryByText(/El IVA por defecto ha cambiado/)).not.toBeInTheDocument()
    expect(screen.getByText('Base exenta')).toBeInTheDocument()
    expect(screen.getByText(MENCION_ORO)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Guardar borrador' }))
    expect(await screen.findByText('Borrador guardado')).toBeInTheDocument()
    expect((peticiones[0]?.cuerpo as { oro_inversion: boolean }).oro_inversion).toBe(true)
  })

  it('un borrador que ya no existe se explica al abrirlo', async () => {
    conBorrador([() => problema(404, 'no-encontrado', 'Este borrador ya no existe.')])
    renderApp(`/facturas/borradores/${ID}`)

    expect(
      await screen.findByText(/Este borrador ya se ha emitido o se ha eliminado/),
    ).toBeVisible()
    expect(screen.getByRole('button', { name: 'Cerrar' })).toBeInTheDocument()
  })
})

describe('«Guardar borrador» en una factura nueva (FR-049)', () => {
  it('guarda sin cliente y el modal pasa al modo borrador', async () => {
    conSesion(crearSesion())
    conCatalogos()
    conFacturacion()
    conBorrador([() => HttpResponse.json(crearBorrador({ cliente: null }))])
    const creados: unknown[] = []
    server.use(
      http.post('*/api/v1/borradores-factura', async ({ request }) => {
        creados.push(await request.json())
        return HttpResponse.json(crearBorrador({ cliente: null }), { status: 201 })
      }),
    )
    const { router } = renderApp('/facturas/nueva')
    const user = userEvent.setup()

    await screen.findByText('Se asigna al emitir')
    await user.type(screen.getByRole('textbox', { name: 'Descripción de la línea 1' }), 'Anillo')
    await user.type(
      screen.getByRole('textbox', { name: 'Precio unitario sin IVA de la línea 1' }),
      '1.200',
    )
    await user.click(screen.getByRole('button', { name: 'Guardar borrador' }))

    expect(await screen.findByText('Borrador guardado')).toBeInTheDocument()
    expect(creados).toEqual([
      {
        fecha_expedicion: PARAMETROS.hoy,
        cliente_id: null,
        lineas: [{ unidades: '1.00', descripcion: 'Anillo', precio_unitario: '1200.00' }],
        oro_inversion: false,
      },
    ])
    await waitFor(() => {
      expect(router.state.location.pathname).toBe(`/facturas/borradores/${ID}`)
    })
    expect(await screen.findByRole('button', { name: 'Eliminar borrador' })).toBeInTheDocument()
  })
})
