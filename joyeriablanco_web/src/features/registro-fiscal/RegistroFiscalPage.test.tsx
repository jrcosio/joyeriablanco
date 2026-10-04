import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import type {
  ComprobacionSalida,
  EventoSifDetalle,
  EventoSifResumen,
  RegistroCadenaDetalle,
} from '../../api/tipos'
import { conSesion, crearSesion, problema, renderApp } from '../../test/app'
import { server } from '../../test/msw'

const admin = crearSesion({ rol: 'administrador', nombre: 'Luis Martín' })
const HUELLA = 'A'.repeat(64)

function evento(secuencia: number, parcial: Partial<EventoSifResumen> = {}): EventoSifResumen {
  return {
    secuencia,
    tipo_evento: '01',
    fecha_hora_huso_gen: '2026-10-03T09:00:00+02:00',
    huella: HUELLA,
    certificado_titular: 'JOYERIA BLANCO (PRUEBAS)',
    resumen: null,
    ...parcial,
  }
}

const LISTA = [
  evento(3, {
    tipo_evento: '02',
    fecha_hora_huso_gen: '2026-10-03T21:00:00+02:00',
    resumen: 'Parada ordenada del servicio',
  }),
  evento(2, {
    tipo_evento: '10',
    fecha_hora_huso_gen: '2026-10-03T15:00:00+02:00',
    resumen: '1 eventos, 0 altas y 0 anulaciones',
  }),
  evento(1),
]

function detalle(secuencia: number, parcial: Partial<EventoSifDetalle> = {}): EventoSifDetalle {
  const base = LISTA.find((e) => e.secuencia === secuencia) ?? evento(secuencia)
  return {
    ...base,
    datos: {},
    huella_correcta: true,
    firma_correcta: true,
    anterior:
      secuencia > 1
        ? { secuencia: secuencia - 1, encadenamiento_correcto: true, fechas_en_orden: true }
        : null,
    siguiente:
      secuencia < 3
        ? { secuencia: secuencia + 1, encadenamiento_correcto: true, fechas_en_orden: true }
        : null,
    ...parcial,
  }
}

function conEventos(
  elementos: EventoSifResumen[] = LISTA,
  detalles: Record<number, EventoSifDetalle> = {},
) {
  const consultas: URLSearchParams[] = []
  server.use(
    http.get('*/api/v1/registro-fiscal/eventos', ({ request }) => {
      const parametros = new URL(request.url).searchParams
      consultas.push(parametros)
      const tipo = parametros.get('tipo')
      const filtrados = tipo ? elementos.filter((e) => e.tipo_evento === tipo) : elementos
      return HttpResponse.json({
        elementos: filtrados,
        total: filtrados.length,
        pagina: 1,
        tamano: 25,
      })
    }),
    http.get('*/api/v1/registro-fiscal/eventos/:secuencia', ({ params }) => {
      const secuencia = Number(params.secuencia)
      return HttpResponse.json(detalles[secuencia] ?? detalle(secuencia))
    }),
  )
  return consultas
}

describe('Registro fiscal → Eventos (004, FR-016)', () => {
  it('lista los eventos del más reciente al más antiguo, con su tipo y su resumen', async () => {
    conSesion(admin)
    conEventos()
    renderApp('/registro-fiscal')

    expect(await screen.findByRole('heading', { name: 'Registro fiscal' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Eventos' })).toHaveAttribute('aria-selected', 'true')
    const tabla = await screen.findByRole('table', { name: 'Registro de eventos' })
    const filas = within(tabla).getAllByRole('row').slice(1)
    expect(filas.map((f) => within(f).getAllByRole('cell')[1]?.textContent)).toEqual([
      '02 Fin del funcionamiento',
      '10 Resumen de eventos',
      '01 Inicio del funcionamiento',
    ])
    expect(within(tabla).getByText('Parada ordenada del servicio')).toBeInTheDocument()
  })

  it('filtra por tipo y lo guarda en la URL', async () => {
    conSesion(admin)
    const consultas = conEventos()
    renderApp('/registro-fiscal?tipo=10')

    const tabla = await screen.findByRole('table', { name: 'Registro de eventos' })
    expect(within(tabla).getAllByRole('row')).toHaveLength(2)
    expect(consultas.at(-1)?.get('tipo')).toBe('10')
  })

  it('sin eventos lo dice, y con un filtro sin resultados también', async () => {
    conSesion(admin)
    conEventos([])
    renderApp('/registro-fiscal')
    expect(await screen.findByText('Todavía no hay eventos')).toBeInTheDocument()
  })

  it('con un filtro sin resultados lo distingue', async () => {
    conSesion(admin)
    conEventos([])
    renderApp('/registro-fiscal?tipo=04')
    expect(await screen.findByText('No hay eventos con este filtro')).toBeInTheDocument()
  })

  it('si la API falla, muestra el error', async () => {
    conSesion(admin)
    server.use(
      http.get('*/api/v1/registro-fiscal/eventos', () => problema(500, 'error', 'Error interno')),
    )
    renderApp('/registro-fiscal')
    expect(await screen.findByText('No se han podido cargar los datos')).toBeInTheDocument()
  })

  it('el detalle comprueba huella y firma y salta al anterior y al siguiente (art. 7.h)', async () => {
    conSesion(admin)
    conEventos(LISTA, {
      2: detalle(2, {
        datos: { ResumenEventos: { NumeroDeRegistrosFacturacionAltaGenerados: '0' } },
        anterior: { secuencia: 1, encadenamiento_correcto: false, fechas_en_orden: true },
      }),
    })
    renderApp('/registro-fiscal')
    const user = userEvent.setup()

    // La tabla y las tarjetas de móvil están las dos en el DOM: se usa la de la tabla.
    const [ver] = await screen.findAllByRole('button', {
      name: 'Ver el evento nº 2: Resumen de eventos',
    })
    if (!ver) throw new Error('Sin botón de detalle')
    await user.click(ver)

    const modal = await screen.findByRole('dialog', { name: 'Evento nº 2 · Resumen de eventos' })
    expect(within(modal).getByText('Huella correcta')).toBeInTheDocument()
    expect(within(modal).getByText('Firma correcta')).toBeInTheDocument()
    expect(
      within(modal).getByText('ResumenEventos › NumeroDeRegistrosFacturacionAltaGenerados:'),
    ).toBeInTheDocument()
    expect(within(modal).getByText('Encadenamiento incorrecto')).toBeInTheDocument()
    expect(within(modal).getAllByText('Fechas en orden')).toHaveLength(2)

    await user.click(within(modal).getByRole('button', { name: 'Evento anterior (nº 1)' }))
    expect(
      await screen.findByRole('dialog', { name: 'Evento nº 1 · Inicio del funcionamiento' }),
    ).toBeInTheDocument()
    expect(screen.getByText('Evento anterior: no hay.')).toBeInTheDocument()
  })

  it('un empleado no puede entrar', async () => {
    conSesion(crearSesion({ rol: 'empleado' }))
    conEventos()
    renderApp('/registro-fiscal')
    expect(await screen.findByRole('heading', { name: /Acceso denegado/ })).toBeInTheDocument()
  })
})

function registro(
  secuencia: number,
  parcial: Partial<RegistroCadenaDetalle> = {},
): RegistroCadenaDetalle {
  return {
    secuencia,
    tipo: 'alta',
    num_serie: `FAC-2026-000${String(secuencia)}`,
    factura_id: `0192f0c0-0000-7000-8000-00000000000${String(secuencia)}`,
    fecha_hora_huso_gen: '2026-10-03T10:00:00+02:00',
    huella: HUELLA,
    certificado_titular: 'JOYERIA BLANCO (PRUEBAS)',
    huella_correcta: true,
    firma_correcta: true,
    anterior:
      secuencia > 1
        ? { secuencia: secuencia - 1, encadenamiento_correcto: true, fechas_en_orden: true }
        : null,
    siguiente: { secuencia: secuencia + 1, encadenamiento_correcto: true, fechas_en_orden: false },
    ...parcial,
  }
}

describe('Registro fiscal → Cadena (004, FR-020; Orden, art. 7.h)', () => {
  it('llega con la secuencia en la URL, muestra el registro y salta al anterior', async () => {
    conSesion(admin)
    conEventos()
    server.use(
      http.get('*/api/v1/registro-fiscal/registros/:secuencia', ({ params }) =>
        Number(params.secuencia) > 9
          ? problema(404, 'no-encontrado', 'El registro no existe.')
          : HttpResponse.json(registro(Number(params.secuencia))),
      ),
    )
    renderApp('/registro-fiscal?pestana=cadena&secuencia=2')
    const user = userEvent.setup()

    expect(
      await screen.findByRole('heading', { name: 'Registro de alta nº 2' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Cadena' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('link', { name: 'FAC-2026-0002' })).toBeInTheDocument()
    expect(screen.getByText('Huella correcta')).toBeInTheDocument()
    expect(screen.getAllByText('Correcto')).toHaveLength(3)
    expect(screen.getByText('Incorrecto')).toBeInTheDocument() // las fechas del siguiente

    await user.click(screen.getByRole('button', { name: 'Anterior (nº 1)' }))
    expect(
      await screen.findByRole('heading', { name: 'Registro de alta nº 1' }),
    ).toBeInTheDocument()
    expect(screen.getByText('Anterior: no hay.')).toBeInTheDocument()

    await user.clear(screen.getByRole('textbox', { name: 'Número de registro' }))
    await user.type(screen.getByRole('textbox', { name: 'Número de registro' }), '12')
    await user.click(screen.getByRole('button', { name: 'Ver registro' }))
    expect(await screen.findByText('No existe el registro nº 12.')).toBeInTheDocument()
  })
})

describe('Registro fiscal → Comprobar integridad (004, FR-017)', () => {
  function conComprobacion(resultado: ComprobacionSalida | 'sin-certificado') {
    const cuerpos: unknown[] = []
    server.use(
      http.post('*/api/v1/registro-fiscal/comprobaciones', async ({ request }) => {
        cuerpos.push(await request.json())
        if (resultado === 'sin-certificado') {
          return problema(
            409,
            'emision-no-disponible',
            'No se puede comprobar: sus eventos se firman y el certificado de firma no es utilizable.',
          )
        }
        return HttpResponse.json(resultado, { status: 201 })
      }),
    )
    return cuerpos
  }

  it('una cadena íntegra lo dice con los recuentos', async () => {
    conSesion(admin)
    conEventos()
    const cuerpos = conComprobacion({ integra: true, registros: 12, eventos: 7, anomalias: [] })
    renderApp('/registro-fiscal?pestana=comprobar')
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Comprobar integridad' }))

    expect(await screen.findByText('Íntegra')).toBeInTheDocument()
    expect(
      screen.getByText(/12 registros de facturación y 7 de evento comprobados, sin anomalías/),
    ).toBeInTheDocument()
    expect(cuerpos).toEqual([{ desde_secuencia: null, hasta_secuencia: null }])
  })

  it('con un rango lo envía, y las anomalías se listan con su tipo y su registro', async () => {
    conSesion(admin)
    conEventos()
    const cuerpos = conComprobacion({
      integra: false,
      registros: 2,
      eventos: 7,
      anomalias: [
        {
          cadena: 'facturacion',
          tipo_anomalia: '01',
          descripcion: 'La huella no coincide con los datos',
          secuencia: 3,
        },
      ],
    })
    renderApp('/registro-fiscal?pestana=comprobar')
    const user = userEvent.setup()

    await user.type(await screen.findByRole('textbox', { name: 'Desde el registro nº' }), '2')
    await user.type(screen.getByRole('textbox', { name: 'Hasta el registro nº' }), '3')
    await user.click(screen.getByRole('button', { name: 'Comprobar integridad' }))

    expect(
      await screen.findByText(/Registro de facturación nº 3 · Anomalía 01 \(Integridad-huella\)/),
    ).toBeInTheDocument()
    expect(screen.getByText('La huella no coincide con los datos')).toBeInTheDocument()
    expect(cuerpos).toEqual([{ desde_secuencia: 2, hasta_secuencia: 3 }])
  })

  it('un rango al revés no se envía', async () => {
    conSesion(admin)
    conEventos()
    const cuerpos = conComprobacion({ integra: true, registros: 0, eventos: 0, anomalias: [] })
    renderApp('/registro-fiscal?pestana=comprobar')
    const user = userEvent.setup()

    await user.type(await screen.findByRole('textbox', { name: 'Desde el registro nº' }), '5')
    await user.type(screen.getByRole('textbox', { name: 'Hasta el registro nº' }), '2')
    await user.click(screen.getByRole('button', { name: 'Comprobar integridad' }))

    expect(screen.getByText('No puede ser menor que «desde».')).toBeInTheDocument()
    expect(cuerpos).toEqual([])
  })

  it('sin certificado muestra el error de la API', async () => {
    conSesion(admin)
    conEventos()
    conComprobacion('sin-certificado')
    renderApp('/registro-fiscal?pestana=comprobar')
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: 'Comprobar integridad' }))

    expect(await screen.findByText(/el certificado de firma no es utilizable/)).toBeInTheDocument()
  })
})
