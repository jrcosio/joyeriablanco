import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { urlPdfListado } from '../../lib/impresion'
import type { FiltrosDocumentos } from '../../lib/filtros-documentos'
import { ImprimirListado } from './ImprimirListado'

const FILTROS: FiltrosDocumentos = {
  q: 'maria',
  anio: 2026,
  mes: 3,
  orden: 'total_desc',
  pagina: 2,
}
const FACTURAS = { href: urlPdfListado('facturas', FILTROS), documentos: 'facturas' }

describe('Imprimir el listado filtrado (003, US2)', () => {
  it('con resultados, abre el PDF del filtro actual en una pestaña nueva y sin la página', () => {
    render(<ImprimirListado {...FACTURAS} total={130} cargando={false} />)

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
    render(<ImprimirListado {...FACTURAS} total={undefined} cargando />)

    expect(screen.getByRole('button', { name: 'Imprimir listado' })).toBeDisabled()
    expect(screen.queryByRole('link')).toBeNull()
  })

  it('desactivado con su motivo accesible si no hay resultados (FR-018, FR-031)', () => {
    render(<ImprimirListado {...FACTURAS} total={0} cargando={false} />)

    const boton = screen.getByRole('button', { name: 'Imprimir listado' })
    expect(boton).toBeDisabled()
    expect(boton).toHaveAccessibleDescription('No hay facturas que imprimir con este filtro')
  })

  it('desactivado con su motivo si el filtro supera las 5.000 facturas', () => {
    const { rerender } = render(<ImprimirListado {...FACTURAS} total={5000} cargando={false} />)
    expect(screen.getByRole('link', { name: 'Imprimir listado' })).toBeInTheDocument()

    rerender(<ImprimirListado {...FACTURAS} total={5001} cargando={false} />)

    const boton = screen.getByRole('button', { name: 'Imprimir listado' })
    expect(boton).toBeDisabled()
    expect(boton).toHaveAccessibleDescription(
      'El listado impreso admite hasta 5.000 facturas: acota el filtro, por ejemplo por año',
    )
  })
})

describe('Imprimir el listado de presupuestos (005, FR-030)', () => {
  it('abre el PDF de presupuestos del filtro, y sus motivos hablan de presupuestos', () => {
    const PRESUPUESTOS = {
      href: urlPdfListado('presupuestos', FILTROS),
      documentos: 'presupuestos',
    }
    const { rerender } = render(<ImprimirListado {...PRESUPUESTOS} total={10} cargando={false} />)
    expect(screen.getByRole('link', { name: 'Imprimir listado' })).toHaveAttribute(
      'href',
      '/api/v1/presupuestos/listado/pdf?q=maria&anio=2026&mes=3&orden=total_desc',
    )

    rerender(<ImprimirListado {...PRESUPUESTOS} total={0} cargando={false} />)
    expect(screen.getByRole('button', { name: 'Imprimir listado' })).toHaveAccessibleDescription(
      'No hay presupuestos que imprimir con este filtro',
    )

    rerender(<ImprimirListado {...PRESUPUESTOS} total={5001} cargando={false} />)
    expect(screen.getByRole('button', { name: 'Imprimir listado' })).toHaveAccessibleDescription(
      'El listado impreso admite hasta 5.000 presupuestos: acota el filtro, por ejemplo por año',
    )
  })
})
