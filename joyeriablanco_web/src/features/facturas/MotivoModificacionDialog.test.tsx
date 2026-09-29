import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { MotivoModificacionDialog } from './MotivoModificacionDialog'

function abrir(parcial: Partial<Parameters<typeof MotivoModificacionDialog>[0]> = {}) {
  const onConfirmar = vi.fn()
  render(
    <MotivoModificacionDialog
      isOpen
      onOpenChange={vi.fn()}
      numSerie="FAC-2026-0007"
      esRectificativa={false}
      proximoNumero="FAC-2026-0012"
      ivaOriginal="21.00"
      ivaVigente="21.00"
      enviando={false}
      onConfirmar={onConfirmar}
      {...parcial}
    />,
  )
  return {
    onConfirmar,
    dialogo: screen.getByRole('alertdialog', { name: 'Motivo de la modificación' }),
  }
}

describe('Motivo de la modificación (FR-024)', () => {
  it('«no debió emitirse» explica que se anula y se reemite con el siguiente número', async () => {
    const { onConfirmar, dialogo } = abrir()
    const user = userEvent.setup()

    await user.click(within(dialogo).getByRole('radio', { name: /no debió emitirse/ }))
    expect(within(dialogo).queryByRole('radiogroup', { name: /Causa/ })).not.toBeInTheDocument()
    expect(within(dialogo).getByRole('status')).toHaveTextContent(
      'Se anulará FAC-2026-0007 y se emitirá una factura nueva con el siguiente número (previsto FAC-2026-0012).',
    )
    await user.type(
      within(dialogo).getByRole('textbox', { name: /Explica el motivo/ }),
      'Número mal',
    )
    await user.click(within(dialogo).getByRole('button', { name: 'Confirmar' }))

    expect(onConfirmar).toHaveBeenCalledWith({
      motivo: 'no_debio_emitirse',
      causa: null,
      motivo_texto: 'Número mal',
    })
  })

  it('«ya entregada» pide la causa (R1 o R4) y anuncia la rectificativa', async () => {
    const { onConfirmar, dialogo } = abrir()
    const user = userEvent.setup()

    await user.click(within(dialogo).getByRole('radio', { name: /ya entregada/ }))
    const causas = within(dialogo).getByRole('radiogroup', { name: /Causa de la rectificación/ })
    expect(
      within(causas)
        .getAllByRole('radio')
        .map((r) => r.closest('label')?.textContent),
    ).toEqual([
      expect.stringContaining('Rectificativa R1'),
      expect.stringContaining('Rectificativa R4'),
    ])
    expect(within(dialogo).getByRole('status')).toHaveTextContent(
      'Se emitirá una factura rectificativa de la serie REC que sustituye a FAC-2026-0007',
    )
    await user.type(within(dialogo).getByRole('textbox', { name: /Explica el motivo/ }), 'Talla')
    await user.click(within(dialogo).getByRole('button', { name: 'Confirmar' }))
    expect(await within(dialogo).findByText('Elige la causa.')).toBeInTheDocument()
    expect(onConfirmar).not.toHaveBeenCalled()

    await user.click(within(causas).getByRole('radio', { name: /Error en datos/ }))
    await user.click(within(dialogo).getByRole('button', { name: 'Confirmar' }))
    expect(onConfirmar).toHaveBeenCalledWith({
      motivo: 'factura_entregada',
      causa: 'error_datos',
      motivo_texto: 'Talla',
    })
  })

  it('exige el motivo y el texto', async () => {
    const { onConfirmar, dialogo } = abrir()
    const user = userEvent.setup()

    await user.click(within(dialogo).getByRole('button', { name: 'Confirmar' }))

    expect(within(dialogo).getByText('Elige el motivo.')).toBeInTheDocument()
    expect(within(dialogo).getByText('Campo obligatorio.')).toBeInTheDocument()
    expect(onConfirmar).not.toHaveBeenCalled()
  })

  it('en una rectificativa solo ofrece «ya entregada»', () => {
    const { dialogo } = abrir({ esRectificativa: true })

    const radios = within(dialogo).getAllByRole('radio')
    expect(radios).toHaveLength(3) // el motivo único y las dos causas
    expect(within(dialogo).queryByRole('radio', { name: /no debió emitirse/ })).toBeNull()
    expect(within(dialogo).getByRole('radio', { name: /ya entregada/ })).toBeChecked()
  })

  it('avisa si el IVA vigente no es el de la factura original', () => {
    const { dialogo } = abrir({ ivaOriginal: '10.00', ivaVigente: '21.00' })

    expect(
      within(dialogo).getByText(/tiene un IVA del 10 %; la factura nueva se emitirá con el 21 %/),
    ).toBeInTheDocument()
  })
})
