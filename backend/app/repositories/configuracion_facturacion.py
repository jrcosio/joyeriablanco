"""Acceso a la configuración de facturación: una única fila (data-model)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.configuracion_facturacion import ID_UNICO, ConfiguracionFacturacion


async def get(session: AsyncSession, *, for_update: bool = False) -> ConfiguracionFacturacion:
    consulta = (
        select(ConfiguracionFacturacion)
        .where(ConfiguracionFacturacion.id == ID_UNICO)
        .execution_options(populate_existing=True)
    )
    if for_update:
        # Solo la fila de configuración: las relaciones van por LEFT JOIN y no se bloquean.
        consulta = consulta.with_for_update(of=ConfiguracionFacturacion)
    configuracion = (await session.execute(consulta)).unique().scalar_one_or_none()
    if configuracion is None:  # la crea la migración 0005: nunca debería faltar
        msg = "Falta la fila de configuracion_facturacion"
        raise RuntimeError(msg)
    return configuracion
