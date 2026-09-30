import { describe, expect, it } from 'vitest'
import {
  aApi,
  calcularTotales,
  desdeApi,
  formatearCantidad,
  formatearEuros,
  importeLinea,
  parsearEntrada,
} from './dinero'

/**
 * Misma política de redondeo que el servidor (research R-10 y R-11) y mismos casos que
 * `backend/tests/unit/domain/test_importes.py`: si divergieran, la previsualización engañaría.
 */
describe('parsearEntrada (formato español)', () => {
  it.each([
    ['1.200,50', 120050n],
    ['1200,5', 120050n],
    ['45', 4500n],
    ['0,125', null], // más de dos decimales
    ['1.200', 120000n], // punto de miles
    ['12.5', 1250n], // punto seguido de 1-2 cifras: decimal
    ['12.50', 1250n],
    ['  7 ', 700n],
    ['', null],
    ['-3', null],
    ['1,2,3', null],
    ['abc', null],
  ])('%s → %s', (texto, esperado) => {
    expect(parsearEntrada(texto)).toBe(esperado)
  })
})

describe('desdeApi y aApi', () => {
  it('lee y escribe el texto decimal con punto de la API', () => {
    expect(desdeApi('1200.50')).toBe(120050n)
    expect(desdeApi('0.00')).toBe(0n)
    expect(aApi(120050n)).toBe('1200.50')
    expect(aApi(5n)).toBe('0.05')
    expect(aApi(0n)).toBe('0.00')
  })
})

describe('formatearEuros', () => {
  // Intl separa la cifra y el símbolo con un espacio de no separación (U+00A0).
  it('usa separador de miles siempre y coma decimal', () => {
    expect(formatearEuros(156090n)).toBe('1.560,90\u00a0€')
    expect(formatearEuros(4500n)).toBe('45,00\u00a0€')
    expect(formatearEuros(0n)).toBe('0,00\u00a0€')
  })

  it('formatea cantidades sin símbolo', () => {
    expect(formatearCantidad(150n)).toBe('1,50')
  })
})

describe('importeLinea (medio céntimo alejándose de cero)', () => {
  it.each([
    [50n, 25n, 13n], // 0,5 × 0,25 = 0,125 → 0,13
    [150n, 3333n, 5000n], // 1,5 × 33,33 = 49,995 → 50,00
    [225n, 1010n, 2273n], // 2,25 × 10,10 = 22,725 → 22,73
    [200n, 4500n, 9000n],
  ])('%s × %s = %s', (unidades, precio, esperado) => {
    expect(importeLinea(unidades, precio)).toBe(esperado)
  })
})

describe('calcularTotales', () => {
  it('reproduce el ejemplo de la captura', () => {
    const totales = calcularTotales(
      [
        { unidades: 100n, precio: 120000n },
        { unidades: 200n, precio: 4500n },
      ],
      2100n,
    )

    expect(totales).toEqual({ base: 129000n, cuota: 27090n, total: 156090n })
  })

  it('la cuota con medio céntimo exacto sube: 0,50 al 21 % = 0,105 → 0,11', () => {
    expect(calcularTotales([{ unidades: 100n, precio: 50n }], 2100n).cuota).toBe(11n)
  })

  it('la base es la suma de las líneas ya redondeadas', () => {
    const linea = { unidades: 50n, precio: 25n }

    expect(calcularTotales([linea, linea, linea], 2100n).base).toBe(39n)
  })

  it('la cuota se calcula sobre la base: tres líneas de 0,07 dan 0,04', () => {
    const linea = { unidades: 100n, precio: 7n }

    expect(calcularTotales([linea, linea, linea], 2100n)).toEqual({
      base: 21n,
      cuota: 4n,
      total: 25n,
    })
  })

  it('sin líneas todo es cero', () => {
    expect(calcularTotales([], 2100n)).toEqual({ base: 0n, cuota: 0n, total: 0n })
  })

  it('sin tipo (oro de inversión, FR-052) no hay cuota y el total es la base', () => {
    expect(
      calcularTotales(
        [
          { unidades: 100n, precio: 745000n },
          { unidades: 50n, precio: 25n },
        ],
        null,
      ),
    ).toEqual({ base: 745013n, cuota: 0n, total: 745013n })
  })
})
