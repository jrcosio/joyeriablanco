import { describe, expect, it } from 'vitest'
import { claveDia, fechaHora, fechaLarga } from './fechas'

describe('fechas', () => {
  it('formatea la fecha larga como en el mockup, con mayúscula inicial', () => {
    expect(fechaLarga(new Date('2025-05-27T10:00:00Z'))).toBe('Martes, 27 de mayo de 2025')
  })

  it('usa la hora peninsular aunque el instante sea otro día en UTC', () => {
    // 31/12/2025 23:30 UTC = 01/01/2026 00:30 en Madrid
    expect(fechaLarga(new Date('2025-12-31T23:30:00Z'))).toBe('Jueves, 1 de enero de 2026')
    expect(claveDia(new Date('2025-12-31T23:30:00Z'))).toBe('2026-01-01')
  })

  it('formatea fecha y hora cortas', () => {
    expect(fechaHora('2025-05-27T12:32:00Z')).toBe('27/05/2025, 14:32')
  })
})
