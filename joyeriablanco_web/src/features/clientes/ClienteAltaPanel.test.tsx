import { screen, waitFor, within } from '@testing-library/react'
import userEvent, { type UserEvent } from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { conCatalogos, conSesion, crearCliente, crearSesion, renderApp } from '../../test/app'
import { conFacturacion } from '../../test/facturas'
import { server } from '../../test/msw'

const carlos = crearCliente({
  id: '0192f0c0-0000-7000-8000-00000000c002',
  nombre: 'Carlos Martín Ruiz',
  identificacion_numero: '45678901G',
  direccion: 'Calle Larios, 3',
})

function conClientes() {
  const llamadas: string[] = []
  server.use(
    http.get('*/api/v1/clientes', () =>
      HttpResponse.json({ elementos: [], total: 0, pagina: 1, tamano: 25 }),
    ),
    http.get('*/api/v1/clientes/:id', () => HttpResponse.json(carlos)),
    http.post('*/api/v1/clientes', () => {
      llamadas.push('alta')
      return HttpResponse.json(carlos, { status: 201 })
    }),
    http.post('*/api/v1/clientes/:id/reactivacion', () => {
      llamadas.push('reactivacion')
      return HttpResponse.json(carlos)
    }),
  )
  return llamadas
}

function conDuplicado(activo: boolean) {
  server.use(
    http.post('*/api/v1/clientes', () =>
      HttpResponse.json(
        {
          type: '/problemas/duplicado',
          title: 'Ya existe',
          status: 409,
          detail: 'Ya existe un cliente con esta identificación.',
          cliente_existente: { id: carlos.id, nombre: carlos.nombre, activo },
        },
        { status: 409 },
      ),
    ),
  )
}

/** Abre el modal de factura con una línea escrita y, encima, el alta de cliente. */
async function abrirAlta(): Promise<UserEvent> {
  const user = userEvent.setup()
  renderApp('/facturas/nueva')
  await screen.findByText('Se asigna al emitir')
  await user.type(screen.getByRole('textbox', { name: 'Descripción de la línea 1' }), 'Anillo')
  await user.click(screen.getByRole('button', { name: 'Nuevo cliente' }))
  await screen.findByRole('dialog', { name: 'Nuevo cliente' })
  return user
}

async function rellenarMinimo(user: UserEvent) {
  await user.type(await screen.findByLabelText(/Nombre o razón social/), 'Carlos Martín Ruiz')
  await user.type(screen.getByLabelText(/Número de identificación/), '45678901G')
}

describe('Alta de cliente desde el modal de factura (FR-046)', () => {
  beforeEach(() => {
    conSesion(crearSesion())
    conCatalogos()
    conFacturacion()
  })

  it('al guardar vuelve a la factura con el cliente elegido y lo escrito intacto', async () => {
    const llamadas = conClientes()
    const user = await abrirAlta()

    await rellenarMinimo(user)
    await user.click(screen.getByRole('button', { name: 'Crear cliente' }))

    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: 'Nuevo cliente' })).not.toBeInTheDocument()
    })
    expect(llamadas).toEqual(['alta'])
    expect(screen.getByRole('combobox', { name: /Cliente/ })).toHaveValue(
      'Carlos Martín Ruiz · 45678901G',
    )
    expect(await screen.findByText('Calle Larios, 3')).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: 'Descripción de la línea 1' })).toHaveValue('Anillo')
  })

  it('al cancelar vuelve sin cambios y el foco regresa a «Nuevo cliente»', async () => {
    const llamadas = conClientes()
    const user = await abrirAlta()

    await user.click(
      within(screen.getByRole('dialog', { name: 'Nuevo cliente' })).getByRole('button', {
        name: 'Cancelar',
      }),
    )

    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: 'Nuevo cliente' })).not.toBeInTheDocument()
    })
    expect(llamadas).toEqual([])
    expect(screen.getByRole('combobox', { name: /Cliente/ })).toHaveValue('')
    expect(screen.getByRole('textbox', { name: 'Descripción de la línea 1' })).toHaveValue('Anillo')
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Nuevo cliente' })).toHaveFocus()
    })
  })

  it('Escape cierra solo el panel de cliente', async () => {
    conClientes()
    const user = await abrirAlta()

    await user.keyboard('{Escape}')

    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: 'Nuevo cliente' })).not.toBeInTheDocument()
    })
    expect(screen.getByRole('dialog', { name: 'Nueva factura' })).toBeInTheDocument()
  })

  it('ante un duplicado activo permite usarlo sin salir de la factura', async () => {
    const llamadas = conClientes()
    conDuplicado(true)
    const user = await abrirAlta()

    await rellenarMinimo(user)
    await user.click(screen.getByRole('button', { name: 'Crear cliente' }))
    expect(
      await screen.findByText(/Ya existe un cliente con esta identificación/),
    ).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Ir al cliente' })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Usar este cliente' }))

    await waitFor(() => {
      expect(screen.getByRole('combobox', { name: /Cliente/ })).toHaveValue(
        'Carlos Martín Ruiz · 45678901G',
      )
    })
    expect(llamadas).toEqual([])
  })

  it('ante un duplicado inactivo ofrece reactivarlo, como en Clientes', async () => {
    const llamadas = conClientes()
    conDuplicado(false)
    const user = await abrirAlta()

    await rellenarMinimo(user)
    await user.click(screen.getByRole('button', { name: 'Crear cliente' }))
    expect(await screen.findByText(/\(inactivo\)/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Reactivar y usar' }))

    expect(await screen.findByText('Cliente «Carlos Martín Ruiz» reactivado.')).toBeInTheDocument()
    expect(llamadas).toEqual(['reactivacion'])
    expect(screen.getByRole('combobox', { name: /Cliente/ })).toHaveValue(
      'Carlos Martín Ruiz · 45678901G',
    )
  })
})
