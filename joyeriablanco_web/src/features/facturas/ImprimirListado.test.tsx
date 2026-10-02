import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { FiltrosFacturas } from '../../api/queries/facturas'
import { ImprimirListado } from './ImprimirListado'

const FILTROS: FiltrosFacturas = { q: 'maria', anio: 2026, mes: 3, orden: 'total_desc', pagina: 2 }

describe('Imprimir el listado filtrado (003, US2)', () => {
  it('con resultados, abre el PDF del filtro actual en una pestaña nueva y sin la página', () => {
    render(<ImprimirListado filtros={FILTROS} total={130} cargando={false} />)

    const enlace = screen.getByRole('link', { name: 'Imprimir listado' })
    expect(enlace).toHaveAttribute(
      'href',
      '/api/v1/facturas/listado/pdf?q=maria&anio=2026&mes=3&orden=total_desc',
    )
    expect(enlace).toHaveAttribute('target', '_blank')
    expect(fireEvent.click(enlace)).toBe(true)
    expect(fireEvent.click(enlace)).toBe(false) // doble clic ignorado (FR-023)
  })

  it('desactivado mientras carga el listado', () => {
    render(<ImprimirListado filtros={FILTROS} total={undefined} cargando />)

    expect(screen.getByRole('button', { name: 'Imprimir listado' })).toBeDisabled()
    expect(screen.queryByRole('link')).toBeNull()
  })

  it('desactivado con su motivo accesible si no hay resultados (FR-018, FR-031)', () => {
    render(<ImprimirListado filtros={FILTROS} total={0} cargando={false} />)

    const boton = screen.getByRole('button', { name: 'Imprimir listado' })
    expect(boton).toBeDisabled()
    expect(boton).toHaveAccessibleDescription('No hay facturas que imprimir con este filtro')
  })

  it('desactivado con su motivo si el filtro supera las 5.000 facturas', () => {
    const { rerender } = render(<ImprimirListado filtros={FILTROS} total={5000} cargando={false} />)
    expect(screen.getByRole('link', { name: 'Imprimir listado' })).toBeInTheDocument()

    rerender(<ImprimirListado filtros={FILTROS} total={5001} cargando={false} />)

    const boton = screen.getByRole('button', { name: 'Imprimir listado' })
    expect(boton).toBeDisabled()
    expect(boton).toHaveAccessibleDescription(
      'El listado impreso admite hasta 5.000 facturas: acota el filtro, por ejemplo por año',
    )
  })
})
