import { act, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { IBAN_DEMO } from '../../test/facturas'
import { crearPresupuesto } from '../../test/presupuestos'
import { ImprimirPresupuesto } from './ImprimirPresupuesto'

const ID = crearPresupuesto().id
const URL_BASE = `/api/v1/presupuestos/${ID}/pdf`

function enlace() {
  return screen.getByRole('link', { name: 'Imprimir presupuesto PRE-2026-0003' })
}

describe('Imprimir un presupuesto (005, US2)', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('abre el PDF en una pestaña nueva', () => {
    render(<ImprimirPresupuesto presupuesto={crearPresupuesto()} />)

    expect(enlace()).toHaveAttribute('href', URL_BASE)
    expect(enlace()).toHaveAttribute('target', '_blank')
    expect(enlace()).toHaveAttribute('rel', 'noopener')
    expect(screen.getByRole('group', { name: 'Opciones de impresión' })).toBeInTheDocument()
  })

  it('no ofrece «Duplicado», que es solo de factura', () => {
    const conIban = crearPresupuesto({ emisor: { ...crearPresupuesto().emisor, iban: IBAN_DEMO } })
    render(<ImprimirPresupuesto presupuesto={conIban} />)

    expect(screen.queryByRole('checkbox', { name: 'Duplicado' })).toBeNull()
    expect(screen.queryByText('Duplicado')).toBeNull()
  })

  it('la casilla del número de cuenta solo aparece si tiene IBAN', async () => {
    const usuario = userEvent.setup()
    const { unmount } = render(<ImprimirPresupuesto presupuesto={crearPresupuesto()} />)
    expect(screen.queryByRole('checkbox', { name: 'Incluir número de cuenta' })).toBeNull()
    unmount()

    const conIban = crearPresupuesto({ emisor: { ...crearPresupuesto().emisor, iban: IBAN_DEMO } })
    render(<ImprimirPresupuesto presupuesto={conIban} />)
    const casilla = screen.getByRole('checkbox', { name: 'Incluir número de cuenta' })
    expect(casilla).not.toBeChecked()
    expect(enlace()).toHaveAttribute('href', URL_BASE)

    await usuario.click(casilla)

    expect(casilla).toBeChecked()
    expect(enlace()).toHaveAttribute('href', `${URL_BASE}?iban=true`)
  })

  it('ignora un segundo clic durante 2 s y anuncia «Preparando…»', () => {
    vi.useFakeTimers()
    render(<ImprimirPresupuesto presupuesto={crearPresupuesto()} />)

    expect(fireEvent.click(enlace())).toBe(true)
    expect(enlace()).toHaveTextContent('Preparando…')
    expect(screen.getByRole('status')).toHaveTextContent('Preparando el PDF…')
    expect(fireEvent.click(enlace())).toBe(false)

    act(() => {
      vi.advanceTimersByTime(2000)
    })

    expect(enlace()).toHaveTextContent('Imprimir')
  })
})
