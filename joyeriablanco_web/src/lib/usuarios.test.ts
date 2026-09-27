import { describe, expect, it } from 'vitest'
import { nombreConEstado } from './usuarios'

describe('nombreConEstado', () => {
  it('marca a los usuarios eliminados', () => {
    expect(nombreConEstado({ nombre: 'Lucía Moreno', eliminado: true })).toBe(
      'Lucía Moreno (eliminado)',
    )
    expect(nombreConEstado({ nombre: 'Lucía Moreno', eliminado: false })).toBe('Lucía Moreno')
  })
})
