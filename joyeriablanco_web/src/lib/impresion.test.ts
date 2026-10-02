import { describe, expect, it } from 'vitest'
import { urlPdfFactura, urlPdfListado } from './impresion'

const ID = '0192f0c0-0000-7000-8000-0000000f0001'

describe('URL del PDF de una factura (003, FR-002, FR-010, FR-033)', () => {
  it('sin opciones, solo la ruta', () => {
    expect(urlPdfFactura(ID)).toBe(`/api/v1/facturas/${ID}/pdf`)
    expect(urlPdfFactura(ID, { iban: false, duplicado: false })).toBe(`/api/v1/facturas/${ID}/pdf`)
  })

  it('cada casilla marcada añade su parámetro', () => {
    expect(urlPdfFactura(ID, { iban: true })).toBe(`/api/v1/facturas/${ID}/pdf?iban=true`)
    expect(urlPdfFactura(ID, { duplicado: true })).toBe(`/api/v1/facturas/${ID}/pdf?duplicado=true`)
    expect(urlPdfFactura(ID, { iban: true, duplicado: true })).toBe(
      `/api/v1/facturas/${ID}/pdf?iban=true&duplicado=true`,
    )
  })
})

describe('URL del PDF del listado (003, FR-018)', () => {
  it('sin filtros ni valores por defecto, solo la ruta; nunca la página', () => {
    expect(urlPdfListado({ orden: 'recientes', pagina: 3 })).toBe('/api/v1/facturas/listado/pdf')
    expect(urlPdfListado({ q: '', orden: 'recientes', pagina: 1 })).toBe(
      '/api/v1/facturas/listado/pdf',
    )
  })

  it('los filtros de la pantalla, tal cual', () => {
    const url = urlPdfListado({
      q: 'maria lopez',
      anio: 'todos',
      mes: 3,
      orden: 'total_desc',
      pagina: 2,
    })

    const parametros = new URL(url, 'http://localhost').searchParams
    expect(new URL(url, 'http://localhost').pathname).toBe('/api/v1/facturas/listado/pdf')
    expect(Object.fromEntries(parametros)).toEqual({
      q: 'maria lopez',
      anio: 'todos',
      mes: '3',
      orden: 'total_desc',
    })
  })

  it('un año concreto', () => {
    expect(urlPdfListado({ anio: 2026, orden: 'antiguas', pagina: 1 })).toBe(
      '/api/v1/facturas/listado/pdf?anio=2026&orden=antiguas',
    )
  })
})
