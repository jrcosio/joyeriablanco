"""/v1/configuracion/facturacion: configuración de facturación, solo administradores (US1)."""

from fastapi import APIRouter, Depends

from app.api.deps import AdminSession, DbDep, OrigenDep, require_admin
from app.schemas.configuracion_facturacion import (
    AjusteContadorEntrada,
    AjusteContadorSalida,
    ConfiguracionFacturacionEntrada,
    ConfiguracionFacturacionSalida,
    ContactoSalida,
    DatosEmisorSalida,
)
from app.schemas.usuario import UsuarioReferencia
from app.services import configuracion_facturacion as servicio

router = APIRouter(
    prefix="/configuracion/facturacion",
    tags=["configuracion"],
    dependencies=[Depends(require_admin)],
)


def _salida(estado: servicio.EstadoConfiguracion) -> ConfiguracionFacturacionSalida:
    config = estado.config
    return ConfiguracionFacturacionSalida(
        version=config.version,
        iva_por_defecto=config.iva_por_defecto,
        modalidad=config.modalidad,  # type: ignore[arg-type]
        emisor=DatosEmisorSalida(
            nombre=config.emisor_nombre,
            nif=config.emisor_nif,
            direccion=config.emisor_direccion,
            codigo_postal=config.emisor_codigo_postal,
            localidad=config.emisor_localidad,
            iban=config.emisor_iban,
            provincia=config.emisor_provincia.nombre_visible if config.emisor_provincia else None,
        ),
        emision_posible=not estado.faltan,
        faltan=estado.faltan,
        proximo_numero=estado.proximo_numero,
        modalidad_bloqueada=estado.modalidad_bloqueada,
        tipos_iva_oficiales=list(estado.tipos_iva_oficiales),
        actualizado_en=config.actualizado_en,
        actualizado_por=(
            UsuarioReferencia.from_model(config.actualizado_por) if config.actualizado_por else None
        ),
        contacto=ContactoSalida(
            telefono=config.emisor_telefono,
            correo=config.emisor_correo,
            web=config.emisor_web,
        ),
        pie_factura=config.pie_factura,
        validez_presupuesto_dias=config.validez_presupuesto_dias,
        pie_presupuesto=config.pie_presupuesto,
    )


@router.get("")
async def obtener_configuracion(db: DbDep) -> ConfiguracionFacturacionSalida:
    return _salida(await servicio.get_config(db))


@router.put("")
async def guardar_configuracion(
    datos: ConfiguracionFacturacionEntrada, sesion: AdminSession, db: DbDep, origen: OrigenDep
) -> ConfiguracionFacturacionSalida:
    estado = await servicio.update_config(db, datos, actor=sesion.usuario, origen=origen)
    return _salida(estado)


@router.post("/contador")
async def ajustar_contador(
    datos: AjusteContadorEntrada, sesion: AdminSession, db: DbDep, origen: OrigenDep
) -> AjusteContadorSalida:
    resultado = await servicio.adjust_counter(db, datos, actor=sesion.usuario, origen=origen)
    return AjusteContadorSalida(
        serie="FAC",
        anio=resultado.anio,
        ultimo_usado=resultado.ultimo_usado,
        proximo_numero=resultado.proximo_numero,
        numeros_sin_usar=resultado.numeros_sin_usar,
        aplicado=resultado.aplicado,
    )
