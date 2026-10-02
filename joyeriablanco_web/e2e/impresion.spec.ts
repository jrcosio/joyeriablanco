import { expect, test, type Page } from '@playwright/test'
import { iniciarSesion } from './helpers/acceso'
import { emitirPorLaApi } from './helpers/facturas'

/**
 * Impresión (003, SC-009): se comprueba el enlace de «Imprimir» y se descarga su PDF con la sesión
 * del navegador. No se depende del visor de PDF de Chromium sin interfaz (research R-11).
 */
async function descargarPdf(page: Page, href: string): Promise<Buffer> {
  const respuesta = await page.request.get(href)
  expect(respuesta.status()).toBe(200)
  expect(respuesta.headers()['content-type']).toBe('application/pdf')
  const cuerpo = await respuesta.body()
  expect(cuerpo.subarray(0, 4).toString()).toBe('%PDF')
  return cuerpo
}

test.describe('Imprimir', () => {
  test('una factura desde su consulta, con y sin opciones (US1)', async ({ page }) => {
    await iniciarSesion(page, 'empleado.demo')
    const factura = await emitirPorLaApi(page)

    await page.goto(`/facturas/${factura.id}`)
    const modal = page.getByRole('dialog', { name: `Factura ${factura.num_serie}` })
    const imprimir = modal.getByRole('link', { name: `Imprimir factura ${factura.num_serie}` })
    await expect(imprimir).toHaveAttribute('target', '_blank')
    const base = `/api/v1/facturas/${factura.id}/pdf`
    await expect(imprimir).toHaveAttribute('href', base)
    await descargarPdf(page, base)

    await modal.getByRole('checkbox', { name: 'Duplicado' }).check({ force: true })
    const casillaIban = modal.getByRole('checkbox', { name: 'Incluir número de cuenta' })
    const conIban = (await casillaIban.count()) > 0
    if (conIban) await casillaIban.check({ force: true })

    const esperado = conIban ? `${base}?iban=true&duplicado=true` : `${base}?duplicado=true`
    await expect(imprimir).toHaveAttribute('href', esperado)
    await descargarPdf(page, esperado)
  })
})
