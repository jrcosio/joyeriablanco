import { Search, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Button as AriaButton, Input, Label, SearchField } from 'react-aria-components'
import type { FiltrosClientes as Filtros } from '../../api/queries/clientes'
import type { CatalogosSalida } from '../../api/tipos'
import { campoCaja } from '../../components/ui/field'
import { Select } from '../../components/ui/Select'

const TODAS = '__todas__'

const ORDENES = [
  { id: 'nombre_asc', label: 'Nombre (A–Z)' },
  { id: 'nombre_desc', label: 'Nombre (Z–A)' },
  { id: 'recientes', label: 'Más recientes' },
  { id: 'antiguos', label: 'Más antiguos' },
]
const ESTADOS = [
  { id: 'activos', label: 'Activos' },
  { id: 'inactivos', label: 'Inactivos' },
  { id: 'todos', label: 'Todos' },
]
const TIPOS = [
  { id: TODAS, label: 'Todos los tipos' },
  { id: 'particular', label: 'Particulares' },
  { id: 'empresa', label: 'Empresas' },
]

export interface FiltrosClientesProps {
  filtros: Filtros
  catalogos: CatalogosSalida | undefined
  onChange: (cambios: Partial<Filtros>) => void
}

/** Búsqueda (con espera de 300 ms), provincia, tipo, estado y orden, ligados a la URL (FR-033). */
export function FiltrosClientes({ filtros, catalogos, onChange }: FiltrosClientesProps) {
  const [texto, setTexto] = useState(filtros.q ?? '')
  const [qPrevia, setQPrevia] = useState(filtros.q)
  // Si la búsqueda cambia desde fuera (p. ej. "Limpiar filtros"), se sincroniza el campo.
  if (filtros.q !== qPrevia) {
    setQPrevia(filtros.q)
    setTexto(filtros.q ?? '')
  }

  useEffect(() => {
    if (texto === (filtros.q ?? '')) return
    const id = setTimeout(() => {
      onChange({ q: texto.trim() ? texto : undefined })
    }, 300)
    return () => {
      clearTimeout(id)
    }
  }, [texto, filtros.q, onChange])

  const provincias = [
    { id: TODAS, label: 'Todas las provincias' },
    ...(catalogos?.provincias ?? []).map((p) => ({ id: p.codigo, label: p.nombre_visible })),
  ]

  return (
    <div
      role="search"
      aria-label="Filtrar clientes"
      className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-[minmax(0,2fr)_repeat(4,minmax(0,1fr))]"
    >
      <SearchField
        value={texto}
        onChange={setTexto}
        aria-label="Buscar nombre, NIF o localidad"
        className="group relative md:col-span-2 xl:col-span-1"
      >
        <Label className="sr-only">Buscar nombre, NIF o localidad</Label>
        <Search
          aria-hidden="true"
          className="pointer-events-none absolute top-1/2 left-4 size-4 -translate-y-1/2 text-on-surface-variant"
        />
        <Input
          placeholder="Buscar nombre, NIF o localidad"
          maxLength={100}
          className={`${campoCaja} pr-10 pl-11 [&::-webkit-search-cancel-button]:hidden`}
        />
        <AriaButton
          aria-label="Borrar búsqueda"
          className="absolute top-1/2 right-3 -translate-y-1/2 text-on-surface-variant group-data-[empty]:hidden"
        >
          <X aria-hidden="true" className="size-4" />
        </AriaButton>
      </SearchField>
      <Select
        label="Provincia"
        hideLabel
        options={provincias}
        value={filtros.provincia ?? TODAS}
        onChange={(v) => {
          onChange({ provincia: v && v !== TODAS ? v : undefined })
        }}
      />
      <Select
        label="Tipo"
        hideLabel
        options={TIPOS}
        value={filtros.tipo ?? TODAS}
        onChange={(v) => {
          onChange({ tipo: v === 'particular' || v === 'empresa' ? v : undefined })
        }}
      />
      <Select
        label="Estado"
        hideLabel
        options={ESTADOS}
        value={filtros.estado}
        onChange={(v) => {
          if (v === 'activos' || v === 'inactivos' || v === 'todos') onChange({ estado: v })
        }}
      />
      <Select
        label="Ordenar"
        hideLabel
        options={ORDENES}
        value={filtros.orden}
        onChange={(v) => {
          if (v === 'nombre_asc' || v === 'nombre_desc' || v === 'recientes' || v === 'antiguos') {
            onChange({ orden: v })
          }
        }}
      />
    </div>
  )
}
