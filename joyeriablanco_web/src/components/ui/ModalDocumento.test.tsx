import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { Button } from './Button'
import { Dialog } from './Dialog'
import { ModalDocumento } from './ModalDocumento'

function ConCapaEncima({ onCerrarModal }: { onCerrarModal: () => void }) {
  const [capa, setCapa] = useState(false)
  return (
    <ModalDocumento
      title="Nueva factura"
      isOpen
      onOpenChange={(abierto) => {
        if (!abierto) onCerrarModal()
      }}
      footer={<Button>Emitir factura</Button>}
    >
      <Button
        onPress={() => {
          setCapa(true)
        }}
      >
        Nuevo cliente
      </Button>
      <Dialog title="Alta de cliente" isOpen={capa} onOpenChange={setCapa}>
        <input aria-label="Nombre" />
      </Dialog>
    </ModalDocumento>
  )
}

describe('ModalDocumento', () => {
  it('es un diálogo con título, cuerpo y pie, y atrapa el foco', async () => {
    render(<ConCapaEncima onCerrarModal={vi.fn()} />)
    const user = userEvent.setup()

    const dialogo = screen.getByRole('dialog', { name: 'Nueva factura' })
    expect(dialogo).toContainElement(screen.getByRole('button', { name: 'Emitir factura' }))
    for (let i = 0; i < 5; i++) await user.tab()
    expect(dialogo).toContainElement(document.activeElement as HTMLElement)
  })

  it('Escape pide cerrar: el padre decide (guarda de cambios)', async () => {
    const onCerrarModal = vi.fn()
    render(<ConCapaEncima onCerrarModal={onCerrarModal} />)
    const user = userEvent.setup()

    await user.keyboard('{Escape}')

    expect(onCerrarModal).toHaveBeenCalledOnce()
  })

  it('con una capa encima, Escape cierra solo la de arriba y el foco vuelve al botón', async () => {
    const onCerrarModal = vi.fn()
    render(<ConCapaEncima onCerrarModal={onCerrarModal} />)
    const user = userEvent.setup()

    const boton = screen.getByRole('button', { name: 'Nuevo cliente' })
    await user.click(boton)
    expect(await screen.findByRole('dialog', { name: 'Alta de cliente' })).toBeInTheDocument()
    await user.keyboard('{Escape}')

    expect(screen.queryByRole('dialog', { name: 'Alta de cliente' })).not.toBeInTheDocument()
    expect(screen.getByRole('dialog', { name: 'Nueva factura' })).toBeInTheDocument()
    expect(onCerrarModal).not.toHaveBeenCalled()
    await waitFor(() => {
      expect(boton).toHaveFocus()
    })
  })
})
