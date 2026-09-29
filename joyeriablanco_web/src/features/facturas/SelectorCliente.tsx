import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { ChevronDown } from 'lucide-react'
import { useEffect, useState } from 'react'
import {
  Button as AriaButton,
  ComboBox as AriaComboBox,
  FieldError,
  Group,
  Input,
  Label,
  ListBox,
  ListBoxItem,
  Popover,
  Text,
  type Key,
} from 'react-aria-components'
import { clientesListaQuery } from '../../api/queries/clientes'
import type { ClienteResumenSalida } from '../../api/tipos'
import { cx } from '../../components/ui/cx'
import {
  campoAyuda,
  campoCaja,
  campoContenedor,
  campoError,
  campoEtiqueta,
} from '../../components/ui/field'

function etiqueta(cliente: Pick<ClienteResumenSalida, 'nombre' | 'identificacion_numero'>): string {
  return `${cliente.nombre} · ${cliente.identificacion_numero}`
}

/**
 * Selector de cliente con búsqueda en el servidor (nombre o identificación, sin tildes). Solo
 * ofrece clientes activos: un inactivo no se puede elegir para un documento nuevo (001).
 */
export function SelectorCliente({
  value,
  nombreInicial,
  onChange,
  error,
  isDisabled = false,
}: {
  value: string | null
  /**
   * Texto del cliente ya elegido (p. ej. al reabrir un borrador o tras darlo de alta). Para
   * cambiarlo después, el padre vuelve a montar el selector con otra `key`.
   */
  nombreInicial?: string | undefined
  onChange: (clienteId: string | null) => void
  error?: string | undefined
  isDisabled?: boolean
}) {
  const [texto, setTexto] = useState(nombreInicial ?? '')
  const [busqueda, setBusqueda] = useState('')

  useEffect(() => {
    const temporizador = setTimeout(() => {
      setBusqueda(texto)
    }, 300)
    return () => {
      clearTimeout(temporizador)
    }
  }, [texto])

  const consulta = useQuery({
    ...clientesListaQuery({
      q: busqueda.includes(' · ') ? undefined : busqueda || undefined,
      estado: 'activos',
      orden: 'nombre_asc',
      pagina: 1,
    }),
    placeholderData: keepPreviousData,
  })
  const opciones = consulta.data?.elementos ?? []

  return (
    <AriaComboBox
      items={opciones}
      value={value}
      inputValue={texto}
      onInputChange={setTexto}
      onChange={(clave: Key | null) => {
        const elegido = opciones.find((o) => o.id === clave)
        if (elegido) setTexto(etiqueta(elegido))
        onChange(clave === null ? null : String(clave))
      }}
      allowsEmptyCollection
      menuTrigger="focus"
      isDisabled={isDisabled}
      isInvalid={Boolean(error)}
      isRequired
      className={campoContenedor}
    >
      <Label className={campoEtiqueta}>
        Cliente<span aria-hidden="true"> *</span>
      </Label>
      <Group
        className={cx(
          campoCaja,
          'flex items-center gap-2 px-0 focus-within:border-primary-container',
        )}
      >
        <Input
          placeholder="Buscar por nombre o NIF"
          className="h-full min-w-0 flex-1 bg-transparent px-3 outline-none"
        />
        <AriaButton
          aria-label="Mostrar clientes"
          className="px-3 text-on-surface-variant outline-none"
        >
          <ChevronDown aria-hidden="true" className="size-4" />
        </AriaButton>
      </Group>
      {!error ? (
        <Text slot="description" className={campoAyuda}>
          Solo se muestran los clientes activos.
        </Text>
      ) : null}
      <FieldError className={campoError}>{error}</FieldError>
      <Popover className="min-w-(--trigger-width) border border-primary-container bg-surface-container-lowest shadow-nivel-2">
        <ListBox<ClienteResumenSalida>
          className="max-h-72 overflow-auto p-1 outline-none"
          renderEmptyState={() => (
            <p className="px-3 py-2 body-md text-on-surface-variant">
              Ningún cliente activo coincide.
            </p>
          )}
        >
          {(cliente) => (
            <ListBoxItem
              id={cliente.id}
              textValue={etiqueta(cliente)}
              className="cursor-pointer px-3 py-2 body-md text-on-surface outline-none data-[focused]:bg-surface-container-high data-[selected]:text-primary"
            >
              <span>{cliente.nombre}</span>
              <span className="ml-2 tabular-nums text-on-surface-variant">
                {cliente.identificacion_numero}
              </span>
            </ListBoxItem>
          )}
        </ListBox>
      </Popover>
    </AriaComboBox>
  )
}
