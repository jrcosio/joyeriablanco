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
    modalidad: null,
    emisor: {
      nombre: null,
      nif: null,
      direccion: null,
      codigo_postal: null,
      localidad: null,
      iban: null,
      provincia: null,
    },
    emision_posible: false,
    faltan: ['modalidad', 'emisor.nombre', 'emisor.nif'],
    proximo_numero: 'FAC-2026-0006',
    modalidad_bloqueada: false,
    tipos_iva_oficiales: ['0.00', '4.00', '10.00', '21.00'],
    actualizado_en: '2026-09-29T08:00:00Z',
    actualizado_por: null,
    contacto: { telefono: null, correo: null, web: null },
    pie_factura: null,
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
  it('avisa de lo que falta para emitir, sin clave de régimen ni IBAN obligatorio', async () => {
    conSesion(admin)
    conConfiguracion(crearConfiguracion())
    renderApp('/configuracion/facturacion')

    const aviso = await screen.findByRole('status', { name: /no se puede emitir/i })
    expect(within(aviso).getByText(/modalidad/i)).toBeInTheDocument()
    expect(within(aviso).getByText(/nombre o razón social del emisor/i)).toBeInTheDocument()
    expect(screen.queryByText(/clave de régimen/i)).not.toBeInTheDocument() // R-23
    expect(screen.getByRole('textbox', { name: /IVA por defecto/ })).toHaveValue('21')
    expect(screen.getByRole('textbox', { name: /^IBAN/ })).not.toBeRequired()
  })

  it('avisa mientras se escribe un IVA fuera de la lista y valida el rango (R-20)', async () => {
    conSesion(admin)
    conConfiguracion(crearConfiguracion())
    renderApp('/configuracion/facturacion')
    const user = userEvent.setup()

    const iva = await screen.findByRole('textbox', { name: /IVA por defecto/ })
    await user.clear(iva)
    await user.type(iva, '22')
    expect(
      screen.getByText('22 % no está entre los tipos que admite hoy la AEAT (0, 4, 10 y 21).'),
    ).toBeInTheDocument()

    await user.clear(iva)
    await user.type(iva, '10')
    expect(screen.queryByText(/no está entre los tipos/)).not.toBeInTheDocument()

    await user.clear(iva)
    await user.type(iva, '100')
    await user.click(screen.getByRole('button', { name: 'Guardar configuración' }))
    expect(
      await screen.findByText(
        'Escribe un porcentaje entre 0 y 99,99, con dos decimales como mucho.',
      ),
    ).toBeInTheDocument()
  })

  it('pide confirmación si la API rechaza el tipo y reenvía al confirmar', async () => {
    conSesion(admin)
    conConfiguracion(crearConfiguracion())
    const enviados: { iva_por_defecto: string; confirmar_tipo_iva: boolean }[] = []
    server.use(
      http.put('*/api/v1/configuracion/facturacion', async ({ request }) => {
        const cuerpo = (await request.json()) as (typeof enviados)[number]
        enviados.push(cuerpo)
        if (!cuerpo.confirmar_tipo_iva) {
          return HttpResponse.json(
            {
              type: '/problemas/tipo-iva-sin-confirmar',
              title: 'Confirma el tipo de IVA',
              status: 422,
              detail: 'Ese tipo de IVA no está entre los que la AEAT admite hoy.',
              tipos_oficiales: ['0.00', '4.00', '10.00', '21.00'],
            },
            { status: 422, headers: { 'Content-Type': 'application/problem+json' } },
          )
        }
        return HttpResponse.json(crearConfiguracion({ version: 2, iva_por_defecto: '22.00' }))
      }),
    )
    renderApp('/configuracion/facturacion')
    const user = userEvent.setup()

    const iva = await screen.findByRole('textbox', { name: /IVA por defecto/ })
    await user.clear(iva)
    await user.type(iva, '22')
    await user.click(screen.getByRole('button', { name: 'Guardar configuración' }))

    const dialogo = await screen.findByRole('alertdialog', {
      name: '¿Guardar un tipo de IVA que la AEAT no admite hoy?',
    })
    expect(within(dialogo).getByText(/rechazar los registros/)).toBeInTheDocument()
    await user.click(within(dialogo).getByRole('button', { name: 'Guardar igualmente' }))

    expect(await screen.findByText('Configuración de facturación guardada')).toBeInTheDocument()
    expect(enviados.map((c) => [c.iva_por_defecto, c.confirmar_tipo_iva])).toEqual([
      ['22.00', false],
      ['22.00', true],
    ])
  })

  it('cancelar la confirmación no reenvía nada', async () => {
    conSesion(admin)
    conConfiguracion(crearConfiguracion())
    let llamadas = 0
    server.use(
      http.put('*/api/v1/configuracion/facturacion', () => {
        llamadas += 1
        return problema(422, 'tipo-iva-sin-confirmar', 'Ese tipo no está en la lista.')
      }),
    )
    renderApp('/configuracion/facturacion')
    const user = userEvent.setup()

    const iva = await screen.findByRole('textbox', { name: /IVA por defecto/ })
    await user.clear(iva)
    await user.type(iva, '12,5')
    await user.click(screen.getByRole('button', { name: 'Guardar configuración' }))
    const dialogo = await screen.findByRole('alertdialog')
    await user.click(within(dialogo).getByRole('button', { name: 'Cancelar' }))

    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    expect(llamadas).toBe(1)
    expect(iva).toHaveValue('12,5')
  })

  it('agrupa el IBAN de cuatro en cuatro y lo envía normalizado (R-22)', async () => {
    conSesion(admin)
    const enviados = conConfiguracion(
      crearConfiguracion({
        emisor: { ...crearConfiguracion().emisor, iban: 'DE89370400440532013000' },
      }),
    )
    renderApp('/configuracion/facturacion')
    const user = userEvent.setup()

    const iban = await screen.findByRole('textbox', { name: /^IBAN/ })
    expect(iban).toHaveValue('DE89 3704 0044 0532 0130 00')
    await user.clear(iban)
    await user.type(iban, 'es9121000418450200051332')
    await user.tab()
    expect(iban).toHaveValue('ES91 2100 0418 4502 0005 1332')
    await user.click(screen.getByRole('button', { name: 'Guardar configuración' }))

    expect(await screen.findByText('Configuración de facturación guardada')).toBeInTheDocument()
    expect((enviados[0] as { emisor: { iban: string } }).emisor.iban).toBe(
      'ES9121000418450200051332',
    )
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
        confirmar_tipo_iva: false,
        modalidad: null,
        emisor: {
          nombre: 'Joyería Blanco, S.L.',
          nif: 'B12345674',
          direccion: null,
          codigo_postal: null,
          localidad: null,
          iban: null,
        },
        contacto: { telefono: null, correo: null, web: null },
        pie_factura: null,
      },
    ])
  })

  it('contacto y pie de factura: opcionales, con su ayuda y su contador (003, FR-024, FR-025)', async () => {
    conSesion(admin)
    const enviados = conConfiguracion(
      crearConfiguracion({
        contacto: { telefono: '+34 942 000 000', correo: null, web: 'joyeriablanco.es' },
        pie_factura: 'Gracias por su confianza.',
      }),
    )
    renderApp('/configuracion/facturacion')
    const user = userEvent.setup()

    const telefono = await screen.findByRole('textbox', { name: 'Teléfono' })
    expect(telefono).toHaveValue('+34 942 000 000')
    expect(telefono).not.toBeRequired()
    expect(screen.getByRole('textbox', { name: 'Web' })).toHaveValue('joyeriablanco.es')
    const pie = screen.getByRole('textbox', { name: 'Pie de factura' })
    expect(pie).toHaveValue('Gracias por su confianza.')
    expect(screen.getByText('25 / 600')).toBeInTheDocument()
    expect(
      screen.getByText(/se imprimen en todas las facturas, también en las ya emitidas/i),
    ).toBeInTheDocument()

    await user.clear(telefono)
    await user.type(screen.getByRole('textbox', { name: 'Correo electrónico' }), 'info@joyeria.es')
    await user.clear(pie)
    await user.type(pie, 'Línea 1{Enter}Línea 2')
    await user.click(screen.getByRole('button', { name: 'Guardar configuración' }))

    expect(await screen.findByText('Configuración de facturación guardada')).toBeInTheDocument()
    expect(enviados[0]).toMatchObject({
      contacto: { telefono: null, correo: 'info@joyeria.es', web: 'joyeriablanco.es' },
      pie_factura: 'Línea 1\nLínea 2',
    })
  })

  it('muestra en su campo los errores del contacto y del pie', async () => {
    conSesion(admin)
    conConfiguracion(crearConfiguracion())
    server.use(
      http.put('*/api/v1/configuracion/facturacion', () =>
        HttpResponse.json(
          {
            type: '/problemas/validacion',
            title: 'Datos no válidos',
            status: 422,
            errores: [
              { campo: 'contacto.telefono', mensaje: 'Debe tener al menos 6 dígitos.' },
              { campo: 'contacto.web', mensaje: 'Escribe un dominio.' },
              { campo: 'pie_factura', mensaje: 'Como máximo 600 caracteres.' },
            ],
          },
          { status: 422, headers: { 'Content-Type': 'application/problem+json' } },
        ),
      ),
    )
    renderApp('/configuracion/facturacion')
    const user = userEvent.setup()

    await user.type(await screen.findByRole('textbox', { name: 'Teléfono' }), '94')
    await user.click(screen.getByRole('button', { name: 'Guardar configuración' }))

    expect(await screen.findByText('Debe tener al menos 6 dígitos.')).toBeInTheDocument()
    expect(screen.getByText('Escribe un dominio.')).toBeInTheDocument()
    expect(screen.getByText('Como máximo 600 caracteres.')).toBeInTheDocument()
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
            errores: [
              { campo: 'emisor.nif', mensaje: 'La letra del NIF no es correcta.' },
              { campo: 'emisor.iban', mensaje: 'El dígito de control del IBAN no es correcto.' },
            ],
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
    expect(screen.getByText('El dígito de control del IBAN no es correcto.')).toBeInTheDocument()
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
