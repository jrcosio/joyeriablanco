import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import type { ConfiguracionFacturacionSalida } from '../../api/tipos'
import { conSesion, crearSesion, problema, renderApp } from '../../test/app'
import { server } from '../../test/msw'

const admin = crearSesion({ rol: 'administrador', nombre: 'Luis Martín' })

function crearConfiguracion(
  parcial: Partial<ConfiguracionFacturacionSalida> = {},
): ConfiguracionFacturacionSalida {
  return {
    version: 1,
    iva_por_defecto: '21.00',
    clave_regimen: '01',
    modalidad: null,
    emisor: {
      nombre: null,
      nif: null,
      direccion: null,
      codigo_postal: null,
      localidad: null,
      provincia: null,
    },
    emision_posible: false,
    faltan: ['modalidad', 'emisor.nombre', 'emisor.nif'],
    proximo_numero: 'FAC-2026-0006',
    modalidad_bloqueada: false,
    tipos_iva_admitidos: ['0.00', '4.00', '10.00', '21.00'],
    actualizado_en: '2026-09-29T08:00:00Z',
    actualizado_por: null,
    ...parcial,
  }
}

function conConfiguracion(config: ConfiguracionFacturacionSalida) {
  const enviados: unknown[] = []
  server.use(
    http.get('*/api/v1/configuracion/facturacion', () => HttpResponse.json(config)),
    http.put('*/api/v1/configuracion/facturacion', async ({ request }) => {
      enviados.push(await request.json())
      return HttpResponse.json({ ...config, version: config.version + 1 })
    }),
  )
  return enviados
}

describe('Configuración → Facturación (US1)', () => {
  it('avisa de lo que falta para emitir y solo ofrece los tipos de IVA admitidos', async () => {
    conSesion(admin)
    conConfiguracion(crearConfiguracion())
    renderApp('/configuracion/facturacion')
    const user = userEvent.setup()

    const aviso = await screen.findByRole('status', { name: /no se puede emitir/i })
    expect(within(aviso).getByText(/modalidad/i)).toBeInTheDocument()
    expect(within(aviso).getByText(/nombre o razón social del emisor/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /IVA por defecto/ }))
    const opciones = (await screen.findAllByRole('option')).map((o) => o.textContent)
    expect(opciones).toEqual(['0 %', '4 %', '10 %', '21 %'])
  })

  it('ofrece la modalidad «Sin decidir» y la bloquea con su explicación si ya hay registros', async () => {
    conSesion(admin)
    conConfiguracion(crearConfiguracion({ modalidad: 'verifactu', modalidad_bloqueada: true }))
    renderApp('/configuracion/facturacion')

    const modalidad = await screen.findByRole('button', { name: /Modalidad/ })
    expect(modalidad).toBeDisabled()
    expect(screen.getByText(/ya hay registros de facturación/i)).toBeInTheDocument()
  })

  it('envía el IVA como texto y los datos del emisor, sin campos de más', async () => {
    conSesion(admin)
    const enviados = conConfiguracion(crearConfiguracion())
    renderApp('/configuracion/facturacion')
    const user = userEvent.setup()

    await user.type(
      await screen.findByRole('textbox', { name: /Nombre o razón social/ }),
      'Joyería Blanco, S.L.',
    )
    await user.type(screen.getByRole('textbox', { name: /^NIF/ }), 'B12345674')
    await user.click(screen.getByRole('button', { name: 'Guardar configuración' }))

    expect(await screen.findByText('Configuración de facturación guardada')).toBeInTheDocument()
    expect(enviados).toEqual([
      {
        version: 1,
        iva_por_defecto: '21.00',
        clave_regimen: '01',
        modalidad: null,
        emisor: {
          nombre: 'Joyería Blanco, S.L.',
          nif: 'B12345674',
          direccion: null,
          codigo_postal: null,
          localidad: null,
        },
      },
    ])
  })

  it('muestra los errores del servidor en su campo', async () => {
    conSesion(admin)
    conConfiguracion(crearConfiguracion())
    server.use(
      http.put('*/api/v1/configuracion/facturacion', () =>
        HttpResponse.json(
          {
            type: '/problemas/validacion',
            title: 'Datos no válidos',
            status: 422,
            errores: [{ campo: 'emisor.nif', mensaje: 'La letra del NIF no es correcta.' }],
          },
          { status: 422, headers: { 'Content-Type': 'application/problem+json' } },
        ),
      ),
    )
    renderApp('/configuracion/facturacion')
    const user = userEvent.setup()

    await user.type(await screen.findByRole('textbox', { name: /^NIF/ }), '12345678A')
    await user.click(screen.getByRole('button', { name: 'Guardar configuración' }))

    expect(await screen.findByText('La letra del NIF no es correcta.')).toBeInTheDocument()
  })

  it('ajusta el contador tras mostrar cuántos números quedarán sin usar', async () => {
    conSesion(admin)
    conConfiguracion(crearConfiguracion())
    const cuerpos: { simular: boolean }[] = []
    server.use(
      http.post('*/api/v1/configuracion/facturacion/contador', async ({ request }) => {
        const cuerpo = (await request.json()) as { simular: boolean; proximo_numero: number }
        cuerpos.push(cuerpo)
        return HttpResponse.json({
          serie: 'FAC',
          anio: 2026,
          ultimo_usado: 5,
          proximo_numero: cuerpo.proximo_numero,
          numeros_sin_usar: 137,
          aplicado: !cuerpo.simular,
        })
      }),
    )
    renderApp('/configuracion/facturacion')
    const user = userEvent.setup()

    expect(await screen.findByText('FAC-2026-0006')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Ajustar numeración' }))
    const dialogo = await screen.findByRole('dialog', { name: 'Ajustar la numeración' })
    await user.type(within(dialogo).getByRole('textbox', { name: /Próximo número/ }), '143')
    await user.type(within(dialogo).getByRole('textbox', { name: /Motivo/ }), 'Programa anterior')
    await user.click(within(dialogo).getByRole('button', { name: 'Continuar' }))

    expect(await within(dialogo).findByText(/137 números sin usar/)).toBeInTheDocument()
    await user.click(within(dialogo).getByRole('button', { name: 'Confirmar ajuste' }))

    expect(await screen.findByText('La próxima factura será FAC-2026-0143')).toBeInTheDocument()
    expect(cuerpos.map((c) => c.simular)).toEqual([true, false])
  })

  it('muestra el rechazo del servidor si el número ya está usado', async () => {
    conSesion(admin)
    conConfiguracion(crearConfiguracion())
    server.use(
      http.post('*/api/v1/configuracion/facturacion/contador', () =>
        problema(409, 'contador-no-ajustable', 'El próximo número debe ser mayor que 6.'),
      ),
    )
    renderApp('/configuracion/facturacion')
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Ajustar numeración' }))
    const dialogo = await screen.findByRole('dialog', { name: 'Ajustar la numeración' })
    await user.type(within(dialogo).getByRole('textbox', { name: /Próximo número/ }), '5')
    await user.type(within(dialogo).getByRole('textbox', { name: /Motivo/ }), 'x')
    await user.click(within(dialogo).getByRole('button', { name: 'Continuar' }))

    expect(
      await within(dialogo).findByText('El próximo número debe ser mayor que 6.'),
    ).toBeInTheDocument()
  })
})
