import '@testing-library/jest-dom/vitest'
import { cleanup, configure } from '@testing-library/react'
import { afterAll, afterEach, beforeAll } from 'vitest'
import { vaciarAvisos } from '../components/ui/toast-store'
import { server } from './msw'

// El primer renderizado de cada fichero carga en frío el árbol de rutas: con todos los ficheros en
// paralelo puede pasar de 1 s, la espera por defecto de los `findBy…`.
configure({ asyncUtilTimeout: 3000 })

beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' })
})
afterEach(() => {
  cleanup()
  server.resetHandlers()
  vaciarAvisos()
})
afterAll(() => {
  server.close()
})
