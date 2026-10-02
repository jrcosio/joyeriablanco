import { act, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { crearFactura, IBAN_DEMO } from '../../test/facturas'
import { ImprimirFactura } from './ImprimirFactura'

const ID = crearFactura().id
const URL_BASE = `/api/v1/facturas/${ID}/pdf`

function enlace() {
  return screen.getByRole('link', { name: 'Imprimir factura FAC-2026-0005' })
}

describe('Imprimir una factura (003, US1)', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('abre el PDF en una pestaña nueva', () => {
    render(<ImprimirFactura factura={crearFactura()} />)

    expect(enlace()).toHaveAttribute('href', URL_BASE)
    expect(enlace()).toHaveAttribute('target', '_blank')
    expect(enlace()).toHaveAttribute('rel', 'noopener')
    expect(screen.getByRole('group', { name: 'Opciones de impresión' })).toBeInTheDocument()
  })

  it('la casilla del número de cuenta solo aparece si la factura tiene IBAN (FR-010)', async () => {
    const usuario = userEvent.setup()
    const { unmount } = render(<ImprimirFactura factura={crearFactura()} />)
    expect(screen.queryByRole('checkbox', { name: 'Incluir número de cuenta' })).toBeNull()
    unmount()

    const conIban = crearFactura({ emisor: { ...crearFactura().emisor, iban: IBAN_DEMO } })
    render(<ImprimirFactura factura={conIban} />)
    const casilla = screen.getByRole('checkbox', { name: 'Incluir número de cuenta' })
    expect(casilla).not.toBeChecked()

    await usuario.click(casilla)

    expect(casilla).toBeChecked()
    expect(enlace()).toHaveAttribute('href', `${URL_BASE}?iban=true`)
  })

  it('«Duplicado» desmarcado salvo en una anulada (FR-033)', async () => {
    const usuario = userEvent.setup()
    const { unmount } = render(<ImprimirFactura factura={crearFactura()} />)
    const casilla = screen.getByRole('checkbox', { name: 'Duplicado' })
    expect(casilla).not.toBeChecked()

    await usuario.click(casilla)

    expect(enlace()).toHaveAttribute('href', `${URL_BASE}?duplicado=true`)
    unmount()

    render(<ImprimirFactura factura={crearFactura({ estado: 'anulada' })} />)
    expect(screen.queryByRole('checkbox', { name: 'Duplicado' })).toBeNull()
    expect(enlace()).toBeInTheDocument()
  })

  it('en una rectificada se admiten las dos casillas a la vez', async () => {
    const usuario = userEvent.setup()
    const factura = crearFactura({
      estado: 'rectificada',
      emisor: { ...crearFactura().emisor, iban: IBAN_DEMO },
    })
    render(<ImprimirFactura factura={factura} />)

    await usuario.click(screen.getByRole('checkbox', { name: 'Incluir número de cuenta' }))
    await usuario.click(screen.getByRole('checkbox', { name: 'Duplicado' }))

    expect(enlace()).toHaveAttribute('href', `${URL_BASE}?iban=true&duplicado=true`)
  })

  it('ignora un segundo clic durante 2 s y lo anuncia (FR-023, FR-031)', () => {
    vi.useFakeTimers()
    render(<ImprimirFactura factura={crearFactura()} />)

    expect(fireEvent.click(enlace())).toBe(true)
    expect(enlace()).toHaveTextContent('Preparando…')
    expect(screen.getByRole('status')).toHaveTextContent('Preparando el PDF…')
    expect(fireEvent.click(enlace())).toBe(false) // preventDefault: no abre otra pestaña

    act(() => {
      vi.advanceTimersByTime(2000)
    })

    expect(enlace()).toHaveTextContent('Imprimir')
    expect(fireEvent.click(enlace())).toBe(true)
  })
})
