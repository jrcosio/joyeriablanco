"""Acceso a la configuración de facturación: una única fila (data-model)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.configuracion_facturacion import ID_UNICO, ConfiguracionFacturacion


async def get(session: AsyncSession, *, for_update: bool = False) -> ConfiguracionFacturacion:
    configuracion = await session.get(
        ConfiguracionFacturacion, ID_UNICO, with_for_update=for_update, populate_existing=True
    )
    if configuracion is None:  # la crea la migración 0005: nunca debería faltar
        msg = "Falta la fila de configuracion_facturacion"
        raise RuntimeError(msg)
    return configuracion
