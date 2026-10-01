import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'
import { CampoDecimal } from './CampoDecimal'

function Controlado({ moneda = false, error }: { moneda?: boolean; error?: string }) {
  const [valor, setValor] = useState('')
  return (
    <CampoDecimal
      label="Precio unitario"
      value={valor}
      onChange={setValor}
      moneda={moneda}
      error={error}
    />
  )
}

describe('CampoDecimal', () => {
  it('admite coma decimal y puntos de miles tal cual se escriben', async () => {
    render(<Controlado />)
    const user = userEvent.setup()

    const campo = screen.getByRole('textbox', { name: 'Precio unitario' })
    await user.type(campo, '1.200,50')

    expect(campo).toHaveValue('1.200,50')
    expect(campo).toHaveAttribute('inputmode', 'decimal')
  })

  it('muestra el símbolo € fijo en los importes, oculto a lectores de pantalla', () => {
    render(<Controlado moneda />)

    expect(screen.getByText('€')).toHaveAttribute('aria-hidden', 'true')
  })

  it('anuncia el error junto al campo', () => {
    render(<Controlado error="Formato no válido" />)

    expect(screen.getByRole('textbox', { name: 'Precio unitario' })).toHaveAttribute(
      'aria-invalid',
      'true',
    )
    expect(screen.getByText('Formato no válido')).toBeInTheDocument()
  })

  it('puede ocultar la etiqueta visualmente sin perder el nombre accesible', () => {
    render(
      <CampoDecimal
        label="Unidades de la línea 1"
        value="1"
        onChange={() => undefined}
        etiquetaOculta
      />,
    )

    expect(screen.getByRole('textbox', { name: 'Unidades de la línea 1' })).toBeInTheDocument()
    expect(screen.getByText('Unidades de la línea 1')).toHaveClass('sr-only')
  })
})
