import type { QueryClient } from '@tanstack/react-query'
import {
  createRootRouteWithContext,
  Outlet,
  useRouter,
  type ErrorComponentProps,
} from '@tanstack/react-router'
import { ErrorState } from '../components/ui/ErrorState'
import { NotFoundPage } from '../components/pages/NotFoundPage'
import { ToastRegion } from '../components/ui/Toast'

export interface RouterContext {
  queryClient: QueryClient
}

export const Route = createRootRouteWithContext<RouterContext>()({
  component: RootLayout,
  notFoundComponent: NotFoundPage,
  errorComponent: ErrorGlobal,
})

function RootLayout() {
  return (
    <>
      <Outlet />
      <ToastRegion />
    </>
  )
}

function ErrorGlobal({ error }: ErrorComponentProps) {
  const router = useRouter()
  return (
    <main className="flex min-h-dvh items-center justify-center px-4">
      <ErrorState
        message={error instanceof Error ? error.message : undefined}
        onRetry={() => {
          void router.invalidate()
        }}
      />
    </main>
  )
}
