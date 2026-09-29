import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterAll, afterEach, beforeAll } from 'vitest'
import { vaciarAvisos } from '../components/ui/toast-store'
import { server } from './msw'

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
