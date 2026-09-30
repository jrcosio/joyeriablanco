import { describe, expect, it } from 'vitest'
import { formatearIban, listaTiposIva, textoTipoIva, tipoIvaATexto } from './facturacion'

describe('formatearIban (R-22)', () => {
  it.each([
    ['ES9121000418450200051332', 'ES91 2100 0418 4502 0005 1332'],
    [' es91 2100 0418 4502 0005 1332 ', 'ES91 2100 0418 4502 0005 1332'],
    ['DE89370400440532013000', 'DE89 3704 0044 0532 0130 00'],
    ['', ''],
  ])('%s → %s', (entrada, esperado) => {
    expect(formatearIban(entrada)).toBe(esperado)
  })
})

describe('tipos de IVA', () => {
  it('pasa el tipo de la API al texto que se escribe en el campo', () => {
    expect(tipoIvaATexto('21.00')).toBe('21')
    expect(tipoIvaATexto('12.50')).toBe('12,5')
    expect(tipoIvaATexto('7.25')).toBe('7,25')
  })

  it('enumera la lista oficial con «y» antes del último', () => {
    expect(listaTiposIva(['0.00', '4.00', '10.00', '21.00'])).toBe('0, 4, 10 y 21')
    expect(listaTiposIva(['21.00'])).toBe('21')
    expect(textoTipoIva('12.50')).toBe('12,5 %')
  })
})
