import { useQuery } from '@tanstack/react-query'
import { UserPlus, Users } from 'lucide-react'
import { indicadoresQuery } from '../../api/queries/clientes'
import { Card } from '../../components/ui/Card'
import { Kpi } from '../../components/ui/Kpi'

/** "Clientes activos" y "Nuevos este año" (FR-034). Globales: no dependen de los filtros. */
export function IndicadoresClientes() {
  const { data, isPending } = useQuery(indicadoresQuery)
  return (
    <Card className="grid grid-cols-1 gap-6 px-6 py-5 sm:grid-cols-2 sm:gap-0 md:px-8">
      <div className="sm:pr-8">
        <Kpi
          icon={<Users className="size-9" strokeWidth={1.25} />}
          label="Clientes activos"
          value={data?.activos}
          isLoading={isPending}
        />
      </div>
      <div className="border-t border-primary-container/18 pt-6 sm:border-t-0 sm:border-l sm:pt-0 sm:pl-8">
        <Kpi
          icon={<UserPlus className="size-9" strokeWidth={1.25} />}
          label="Nuevos este año"
          value={data?.nuevos_este_anio}
          isLoading={isPending}
        />
      </div>
    </Card>
  )
}
