import { QueryClient } from '@tanstack/react-query'
import { createRouter } from '@tanstack/react-router'
import { ApiError } from './api/client'
import { configurarPerdidaDeSesion } from './auth/perdida'
import { NotFoundPage } from './components/pages/NotFoundPage'
import { routeTree } from './routeTree.gen'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      // No se reintentan los errores de negocio (4xx): solo los de red o servidor.
      retry: (intentos, error) =>
        intentos < 2 && !(error instanceof ApiError && error.status >= 400 && error.status < 500),
    },
    mutations: { retry: false },
  },
})

export const router = createRouter({
  routeTree,
  context: { queryClient },
  defaultPreload: 'intent',
  defaultPreloadStaleTime: 0,
  scrollRestoration: true,
  defaultNotFoundComponent: NotFoundPage,
})

configurarPerdidaDeSesion(queryClient, router)

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
