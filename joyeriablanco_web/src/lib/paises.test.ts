import { describe, expect, it } from 'vitest'
import { nombrePais, opcionesPaises } from './paises'

describe('paises', () => {
  it('muestra el nombre en español', () => {
    expect(nombrePais('DE')).toBe('Alemania')
    expect(nombrePais('es')).toBe('España')
  })

  it('ordena alfabéticamente con España primero', () => {
    const nombres = opcionesPaises(['FR', 'DE', 'ES', 'AT']).map((o) => o.codigo)
    expect(nombres).toEqual(['ES', 'DE', 'AT', 'FR'])
  })
})
