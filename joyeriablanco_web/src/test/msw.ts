import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'

/**
 * Servidor MSW compartido; cada test añade sus handlers con `server.use(...)`. Por defecto no hay
 * alarmas (004): la banda las consulta en todas las pantallas.
 */
export const server = setupServer(
  http.get('*/api/v1/alarmas', () => HttpResponse.json({ alarmas: [] })),
)
