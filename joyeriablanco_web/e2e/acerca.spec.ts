import { expect, test } from '@playwright/test'
import { iniciarSesion } from './helpers/acceso'

/** «Acerca del sistema» y la declaración responsable (004, US5; FR-027, SC-008). */
test.describe('Acerca del sistema', () => {
  test('un empleado abre la declaración desde el menú lateral y la descarga en PDF', async ({
    page,
  }) => {
    await iniciarSesion(page, 'empleado.demo')
    await page.getByRole('link', { name: 'Acerca del sistema' }).first().click()

    await expect(
      page.getByRole('heading', {
        name: 'DECLARACIÓN RESPONSABLE DEL SISTEMA INFORMÁTICO DE FACTURACIÓN',
      }),
    ).toBeVisible()
    await expect(page.getByText('a) Nombre del sistema informático')).toBeVisible()
    await expect(page.getByText(/^l\) Fecha y lugar/)).toBeVisible()

    // Como en 003 (impresion.spec.ts): el enlace abre una pestaña nueva; se pide su PDF con la
    // sesión del navegador.
    const enlace = page.getByRole('link', { name: 'Descargar PDF de la declaración responsable' })
    await expect(enlace).toHaveAttribute('target', '_blank')
    const respuesta = await page.request.get((await enlace.getAttribute('href')) ?? '')
    expect(respuesta.status()).toBe(200)
    expect(respuesta.headers()['content-type']).toBe('application/pdf')
  })
})
