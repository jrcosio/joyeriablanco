import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useState, type ReactNode } from 'react'
import { clienteQuery } from '../../api/queries/clientes'
import type { CatalogosSalida, ClienteEntrada, ClienteSalida } from '../../api/tipos'
import { Button } from '../../components/ui/Button'
import { Chip } from '../../components/ui/Chip'
import { Dialog } from '../../components/ui/Dialog'
import { Drawer } from '../../components/ui/Drawer'
import { Skeleton } from '../../components/ui/Skeleton'
import { fechaHora } from '../../lib/fechas'
import { nombreConEstado } from '../../lib/usuarios'
import { ClienteForm, type ClienteExistente } from './ClienteForm'

const FORM_ID = 'form-cliente'

export interface ClientePanelProps {
  catalogos: CatalogosSalida | undefined
  cliente?: ClienteSalida
  cargando?: boolean
  onGuardar: (cuerpo: ClienteEntrada) => Promise<void>
  onCerrar: () => void
  /** Acciones de ciclo de vida (US4) que se muestran bajo la trazabilidad. */
  acciones?: ReactNode
  accionDuplicado?: (existente: ClienteExistente) => ReactNode
}

/** Panel lateral de alta, ficha y edición de clientes (nivel 2; FR-029, FR-030, FR-058). */
export function ClientePanel({
  catalogos,
  cliente,
  cargando = false,
  onGuardar,
  onCerrar,
  acciones,
  accionDuplicado,
}: ClientePanelProps) {
  const queryClient = useQueryClient()
  const [sucio, setSucio] = useState(false)
  const [confirmarDescarte, setConfirmarDescarte] = useState(false)
  const [conflicto, setConflicto] = useState(false)
  const [guardando, setGuardando] = useState(false)
  const [versionForm, setVersionForm] = useState(0)

  const intentarCerrar = useCallback(() => {
    if (sucio) {
      setConfirmarDescarte(true)
    } else {
      onCerrar()
    }
  }, [sucio, onCerrar])

  const guardar = async (cuerpo: ClienteEntrada) => {
    setGuardando(true)
    try {
      await onGuardar(cuerpo)
      setSucio(false)
    } finally {
      setGuardando(false)
    }
  }

  const recargar = async () => {
    if (!cliente) return
    await queryClient.invalidateQueries({ queryKey: clienteQuery(cliente.id).queryKey })
    setConflicto(false)
    setSucio(false)
    setVersionForm((v) => v + 1)
  }

  const titulo = cliente ? cliente.nombre : cargando ? 'Cliente' : 'Nuevo cliente'
  const subtitulo = cliente ? (
    <span className="flex flex-wrap items-center gap-3">
      <Chip tone={cliente.activo ? 'success' : 'danger'}>
        {cliente.activo ? 'Activo' : 'Inactivo'}
      </Chip>
      <span className="tabular-nums">{cliente.identificacion_numero}</span>
    </span>
  ) : undefined

  return (
    <>
      <Drawer
        title={titulo}
        subtitle={subtitulo}
        isOpen
        onOpenChange={(abierto) => {
          if (!abierto) intentarCerrar()
        }}
        footer={
          <>
            <Button variant="secondary" onPress={intentarCerrar}>
              Cancelar
            </Button>
            <Button type="submit" form={FORM_ID} isDisabled={guardando || cargando || !catalogos}>
              {guardando ? 'Guardando…' : cliente ? 'Guardar cambios' : 'Crear cliente'}
            </Button>
          </>
        }
      >
        {cargando || !catalogos ? (
          <div className="flex flex-col gap-5" aria-busy="true" aria-label="Cargando">
            {Array.from({ length: 6 }, (_, i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        ) : (
          <div className="flex flex-col gap-8">
            <ClienteForm
              key={`${cliente?.id ?? 'nuevo'}-${cliente?.version ?? 0}-${versionForm}`}
              formId={FORM_ID}
              catalogos={catalogos}
              {...(cliente ? { cliente } : {})}
              onEnviar={guardar}
              onConflicto={() => {
                setConflicto(true)
              }}
              onDirtyChange={setSucio}
              {...(accionDuplicado ? { accionDuplicado } : {})}
            />
            {cliente ? (
              <section className="flex flex-col gap-3 border-t border-primary-container/18 pt-5">
                <h3 className="label-md text-primary">Trazabilidad</h3>
                <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 body-sm">
                  <dt className="text-on-surface-variant">Creado</dt>
                  <dd className="text-on-surface">
                    {fechaHora(cliente.creado_en)} · {nombreConEstado(cliente.creado_por)}
                  </dd>
                  <dt className="text-on-surface-variant">Última modificación</dt>
                  <dd className="text-on-surface">
                    {fechaHora(cliente.actualizado_en)} · {nombreConEstado(cliente.actualizado_por)}
                  </dd>
                </dl>
                {acciones}
              </section>
            ) : null}
          </div>
        )}
      </Drawer>

      <Dialog
        title="¿Descartar los cambios?"
        role="alertdialog"
        isOpen={confirmarDescarte}
        onOpenChange={setConfirmarDescarte}
      >
        <p className="body-md text-on-surface-variant">
          Hay cambios sin guardar en este cliente. Si cierras el panel, se perderán.
        </p>
        <div className="mt-2 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button
            variant="secondary"
            onPress={() => {
              setConfirmarDescarte(false)
            }}
          >
            Seguir editando
          </Button>
          <Button
            variant="primary"
            onPress={() => {
              setConfirmarDescarte(false)
              onCerrar()
            }}
          >
            Descartar
          </Button>
        </div>
      </Dialog>

      <Dialog
        title="El cliente ha cambiado"
        role="alertdialog"
        isOpen={conflicto}
        onOpenChange={setConflicto}
      >
        <p className="body-md text-on-surface-variant">
          El cliente ha cambiado desde que lo abriste. Puedes recargar los datos actuales (se
          descartarán tus cambios) o seguir con el formulario para copiar lo que necesites.
        </p>
        <div className="mt-2 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button
            variant="secondary"
            onPress={() => {
              setConflicto(false)
            }}
          >
            Seguir editando
          </Button>
          <Button variant="primary" onPress={() => void recargar()}>
            Recargar datos
          </Button>
        </div>
      </Dialog>
    </>
  )
}
