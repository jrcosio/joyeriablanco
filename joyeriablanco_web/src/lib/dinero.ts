/**
 * Importes sin `float` en la web (constitución II; research R-11).
 *
 * Todos los importes son enteros escalados en `bigint`: céntimos para los euros y centésimas para
 * las unidades y los tipos de IVA (21 % = 2100n). La política de redondeo es la misma que la del
 * servidor (research R-10): importe de línea al céntimo, base = suma de líneas, cuota sobre la
 * base y medio céntimo alejándose de cero. La web solo PREVISUALIZA: los importes que valen son
 * los que devuelve la API (constitución VI).
 */

/** Divide redondeando el medio alejándose de cero. */
function dividirRedondeando(dividendo: bigint, divisor: bigint): bigint {
  const cociente = dividendo / divisor
  const resto = dividendo % divisor
  const absoluto = (valor: bigint) => (valor < 0n ? -valor : valor)
  if (2n * absoluto(resto) >= absoluto(divisor)) {
    return cociente + (dividendo < 0n !== divisor < 0n ? -1n : 1n)
  }
  return cociente
}

function desdePartes(entera: string, decimal: string): bigint {
  return BigInt(entera) * 100n + BigInt(decimal.padEnd(2, '0'))
}

/**
 * Texto que escribe el usuario, en formato español: coma decimal y punto de miles opcional
 * («1.200,50»). Sin coma, un punto seguido de 1 o 2 cifras al final se toma como decimal
 * («12.5»). Devuelve `null` si no es un número no negativo con como mucho dos decimales.
 */
export function parsearEntrada(texto: string): bigint | null {
  const limpio = texto.trim()
  if (limpio === '') return null
  let entera: string
  let decimal = ''
  if (limpio.includes(',')) {
    const partes = limpio.split(',')
    if (partes.length !== 2) return null
    const [izquierda = '', derecha = ''] = partes
    if (!/^\d{1,3}(\.\d{3})*$|^\d+$/.test(izquierda) || !/^\d{1,2}$/.test(derecha)) return null
    entera = izquierda.replaceAll('.', '')
    decimal = derecha
  } else if (/^\d+\.\d{1,2}$/.test(limpio)) {
    ;[entera = '', decimal = ''] = limpio.split('.')
  } else if (/^\d{1,3}(\.\d{3})+$|^\d+$/.test(limpio)) {
    entera = limpio.replaceAll('.', '')
  } else {
    return null
  }
  return desdePartes(entera, decimal)
}

/** Texto decimal con punto de la API («1200.50») → céntimos. */
export function desdeApi(texto: string): bigint {
  const coincidencia = /^(-?)(\d+)(?:\.(\d{1,2}))?$/.exec(texto)
  if (!coincidencia) throw new Error(`Importe no válido de la API: ${texto}`)
  const [, signo = '', entera = '0', decimal = ''] = coincidencia
  const valor = desdePartes(entera, decimal)
  return signo === '-' ? -valor : valor
}

/** Céntimos → texto decimal con punto para la API («1200.50»). */
export function aApi(centimos: bigint): string {
  const signo = centimos < 0n ? '-' : ''
  const absoluto = centimos < 0n ? -centimos : centimos
  const entera = absoluto / 100n
  const decimal = (absoluto % 100n).toString().padStart(2, '0')
  return `${signo}${entera.toString()}.${decimal}`
}

const euros = new Intl.NumberFormat('es-ES', {
  style: 'currency',
  currency: 'EUR',
  useGrouping: 'always',
})
const decimales = new Intl.NumberFormat('es-ES', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
  useGrouping: 'always',
})

/** Céntimos → «1.560,90 €». Se formatea el texto decimal, nunca un `number`. */
export function formatearEuros(centimos: bigint): string {
  return euros.format(aApi(centimos) as Intl.StringNumericLiteral)
}

/** Centésimas → «1,50». */
export function formatearCantidad(centesimas: bigint): string {
  return decimales.format(aApi(centesimas) as Intl.StringNumericLiteral)
}

/** Importe de una línea en céntimos: unidades (centésimas) × precio (céntimos), redondeado. */
export function importeLinea(unidades: bigint, precio: bigint): bigint {
  return dividirRedondeando(unidades * precio, 100n)
}

export interface LineaCalculo {
  unidades: bigint
  precio: bigint
}

export interface TotalesCalculo {
  base: bigint
  cuota: bigint
  total: bigint
}

/**
 * Totales de un único tipo de IVA (FR-013): `tipoIva` en centésimas de punto (21 % = 2100n), o
 * `null` en una factura de oro de inversión, sin IVA (FR-052).
 */
export function calcularTotales(
  lineas: readonly LineaCalculo[],
  tipoIva: bigint | null,
): TotalesCalculo {
  const base = lineas.reduce((suma, l) => suma + importeLinea(l.unidades, l.precio), 0n)
  const cuota = tipoIva === null ? 0n : dividirRedondeando(base * tipoIva, 10_000n)
  return { base, cuota, total: base + cuota }
}
