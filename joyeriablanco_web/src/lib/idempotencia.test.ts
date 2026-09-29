import { act, renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { useClaveOperacion } from './idempotencia'

describe('useClaveOperacion', () => {
  it('mantiene la misma clave entre renders (reintentos) y la renueva tras un éxito', () => {
    const { result, rerender } = renderHook(() => useClaveOperacion())
    const primera = result.current.clave

    rerender()
    expect(result.current.clave).toBe(primera)
    expect(primera).toMatch(/^[0-9a-f-]{36}$/)

    act(() => {
      result.current.renovar()
    })
    expect(result.current.clave).not.toBe(primera)
  })
})
