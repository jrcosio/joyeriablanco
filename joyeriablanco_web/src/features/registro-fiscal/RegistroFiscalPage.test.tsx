import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import type { EventoSifDetalle, EventoSifResumen } from '../../api/tipos'
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
