import { setupServer } from 'msw/node'

/** Servidor MSW compartido; cada test añade sus handlers con `server.use(...)`. */
export const server = setupServer()
