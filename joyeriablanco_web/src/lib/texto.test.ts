import { describe, expect, it } from 'vitest'
import { iniciales, normalizar } from './texto'

describe('iniciales', () => {
  it.each([
    ['María López García', 'ML'],
    ['  luis   martín ', 'LM'],
    ['Administrador', 'AD'],
    ['Álvaro Pérez', 'ÁP'],
    ['', '?'],
  ])('%s → %s', (nombre, esperado) => {
    expect(iniciales(nombre)).toBe(esperado)
  })
})

describe('normalizar', () => {
  it('quita tildes y mayúsculas', () => {
    expect(normalizar('María LÓPEZ')).toBe('maria lopez')
  })
})
