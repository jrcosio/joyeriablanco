import { describe, expect, it } from 'vitest'
import { CATALOGOS } from '../../test/app'
import type { CatalogosSalida } from '../../api/tipos'
import { aCuerpo, tiposPermitidos, valoresIniciales } from './cliente-valores'

const catalogos = CATALOGOS as unknown as CatalogosSalida

describe('tiposPermitidos', () => {
  it.each([
    ['ES', ['NIF', '03']],
    ['FR', ['02', '03', '04', '05', '06']],
    ['US', ['03', '04', '05', '06']],
  ])('%s → %j', (pais, esperados) => {
    expect(tiposPermitidos(pais, catalogos).map((t) => t.codigo)).toEqual(esperados)
  })
})

describe('aCuerpo', () => {
  it('convierte los vacíos en null y descarta la provincia que no aplica', () => {
    const cuerpo = aCuerpo({
      ...valoresIniciales(),
      nombre: '  Joyería Serrano ',
      identificacion_numero: ' B12345678 ',
      telefono: '   ',
      pais_residencia: 'FR',
      provincia_codigo: '29',
      provincia_texto: 'Provence',
    })
    expect(cuerpo).toMatchObject({
      nombre: 'Joyería Serrano',
      identificacion_numero: 'B12345678',
      telefono: null,
      correo: null,
      provincia_codigo: null,
      provincia_texto: 'Provence',
    })
  })
})
