import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { AnularFacturaDialog } from './AnularFacturaDialog'

function abrir(reactivara?: string) {
  const onConfirmar = vi.fn()
  render(
    <AnularFacturaDialog
      isOpen
      onOpenChange={vi.fn()}
      numSerie="REC-2026-0001"
      reactivara={reactivara}
      enviando={false}
      onConfirmar={onConfirmar}
    />,
  )
  return { onConfirmar, dialogo: screen.getByRole('alertdialog', { name: /Anular la factura/ }) }
}

describe('Anular una factura (FR-025)', () => {
  it('exige la declaración y el motivo antes de anular', async () => {
    const { onConfirmar, dialogo } = abrir()
    const user = userEvent.setup()

    expect(within(dialogo).getByText(/No se puede deshacer/)).toBeInTheDocument()
    await user.click(within(dialogo).getByRole('button', { name: 'Anular factura' }))
    expect(within(dialogo).getByText('Hace falta la declaración para anular.')).toBeInTheDocument()
    expect(within(dialogo).getByText('Campo obligatorio.')).toBeInTheDocument()

    await user.click(
      within(dialogo).getByRole('checkbox', { name: 'Declaro que esta factura no debió emitirse' }),
    )
    await user.type(within(dialogo).getByRole('textbox', { name: /Motivo/ }), 'Duplicada')
    await user.click(within(dialogo).getByRole('button', { name: 'Anular factura' }))

    expect(onConfirmar).toHaveBeenCalledWith('Duplicada')
  })

  it('en una rectificativa avisa de que la original vuelve a estar vigente (FR-048)', () => {
    const { dialogo } = abrir('FAC-2026-0007')

    expect(within(dialogo).getByRole('status')).toHaveTextContent(
      'FAC-2026-0007 volverá a estar vigente.',
    )
  })
})
