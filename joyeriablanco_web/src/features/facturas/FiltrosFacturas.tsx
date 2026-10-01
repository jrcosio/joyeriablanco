import { Search, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Button as AriaButton, Input, Label, SearchField } from 'react-aria-components'
import type { FiltrosFacturas as Filtros, OrdenFacturas } from '../../api/queries/facturas'
import { campoCaja } from '../../components/ui/field'
import { Select } from '../../components/ui/Select'
import { anioEnCurso } from '../../lib/fechas'

const TODOS = 'todos'
/** Primer año con facturas posibles: la Orden HAC/1177/2024 entra en vigor el 28/10/2024. */
const PRIMER_ANIO = 2024

const MESES = [
  'Enero',
  'Febrero',
  'Marzo',
  'Abril',
  'Mayo',
  'Junio',
  'Julio',
  'Agosto',
  'Septiembre',
  'Octubre',
  'Noviembre',
  'Diciembre',
]

const ORDENES: { id: OrdenFacturas; label: string }[] = [
  { id: 'recientes', label: 'Más recientes' },
  { id: 'antiguas', label: 'Más antiguas' },
  { id: 'total_desc', label: 'Total mayor' },
  { id: 'total_asc', label: 'Total menor' },
]

export const PLACEHOLDER_BUSQUEDA = 'Buscar número, cliente o NIF'

function esOrden(valor: string | null): valor is OrdenFacturas {
  return ORDENES.some((o) => o.id === valor)
}

/** Búsqueda (con espera de 300 ms), año, mes y orden, ligados a la URL (FR-034, FR-035). */
export function FiltrosFacturas({
  filtros,
  onChange,
}: {
  filtros: Filtros
  onChange: (cambios: Partial<Filtros>) => void
}) {
  const [texto, setTexto] = useState(filtros.q ?? '')
  const [qPrevia, setQPrevia] = useState(filtros.q)
  // Si la búsqueda cambia desde fuera (p. ej. «Limpiar filtros»), se sincroniza el campo.
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

  const actual = anioEnCurso()
  const anios = [
    { id: TODOS, label: 'Todos los años' },
    ...Array.from({ length: Math.max(actual - PRIMER_ANIO + 1, 1) }, (_, i) => {
      const anio = String(actual - i)
      return { id: anio, label: anio }
    }),
  ]
  const meses = [
    { id: TODOS, label: 'Todos los meses' },
    ...MESES.map((nombre, i) => ({ id: String(i + 1), label: nombre })),
  ]

  return (
    <div
      role="search"
      aria-label="Filtrar facturas"
      className="grid grid-cols-1 gap-3 md:grid-cols-3 xl:grid-cols-[minmax(0,2fr)_repeat(3,minmax(0,1fr))]"
    >
      <SearchField
        value={texto}
        onChange={setTexto}
        aria-label={PLACEHOLDER_BUSQUEDA}
        className="group relative md:col-span-3 xl:col-span-1"
      >
        <Label className="sr-only">{PLACEHOLDER_BUSQUEDA}</Label>
        <Search
          aria-hidden="true"
          className="pointer-events-none absolute top-1/2 left-4 size-4 -translate-y-1/2 text-on-surface-variant"
        />
        <Input
          placeholder={PLACEHOLDER_BUSQUEDA}
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
        label="Año"
        hideLabel
        options={anios}
        value={String(filtros.anio ?? actual)}
        onChange={(v) => {
          if (!v) return
          const anio = v === TODOS ? TODOS : Number(v)
          onChange({ anio: anio === actual ? undefined : anio })
        }}
      />
      <Select
        label="Mes"
        hideLabel
        options={meses}
        value={filtros.mes ? String(filtros.mes) : TODOS}
        onChange={(v) => {
          onChange({ mes: v && v !== TODOS ? Number(v) : undefined })
        }}
      />
      <Select
        label="Ordenar"
        hideLabel
        options={ORDENES}
        value={filtros.orden}
        onChange={(v) => {
          if (esOrden(v)) onChange({ orden: v })
        }}
      />
    </div>
  )
}
