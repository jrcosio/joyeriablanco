"""Datos de prueba de facturación: configuración completa, clientes facturables y cuerpos de API.

Todo dentro de la transacción del test (se revierte al terminar), salvo que se use con una sesión
propia que confirme, como en los tests de concurrencia.
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tiempo import hoy
from app.models import Cliente
from app.repositories import configuracion_facturacion

NIF_MARIA = "12345678Z"


IBAN_DEMO = "ES9121000418450200051332"


async def configurar_facturacion(
    db: AsyncSession,
    *,
    iva: str = "21",
    modalidad: str | None = "verifactu",
    iban: str | None = None,
) -> None:
    config = await configuracion_facturacion.get(db, for_update=True)
    config.iva_por_defecto = Decimal(iva)
    config.modalidad = modalidad
    config.emisor_iban = iban
    config.emisor_nombre = "Joyería Blanco, S.L."
    config.emisor_nif = "B12345674"
    config.emisor_direccion = "Calle Mayor, 1"
    config.emisor_codigo_postal = "39001"
    config.emisor_localidad = "Santander"
    config.emisor_provincia_codigo = "39"
    await db.flush()


async def crear_cliente(
    db: AsyncSession,
    actor_id: uuid.UUID,
    *,
    nombre: str = "María López García",
    numero: str = NIF_MARIA,
    tipo_identificacion: str = "NIF",
    pais: str = "ES",
    activo: bool = True,
    con_domicilio: bool = True,
) -> Cliente:
    cliente = Cliente(
        tipo="particular",
        nombre=nombre,
        identificacion_pais=pais,
        identificacion_tipo=tipo_identificacion,
        identificacion_numero=numero,
        direccion="Calle Serrano, 45, 2.º A" if con_domicilio else None,
        codigo_postal="28001" if con_domicilio else None,
        localidad="Madrid" if con_domicilio else None,
        provincia_codigo="28" if con_domicilio else None,
        pais_residencia="ES",
        activo=activo,
        creado_por_id=actor_id,
        actualizado_por_id=actor_id,
    )
    db.add(cliente)
    await db.flush()
    return cliente


LINEAS_CAPTURA: list[dict[str, str]] = [
    {
        "unidades": "1",
        "descripcion": "Anillo de oro blanco con diamantes (talla 14)",
        "precio_unitario": "1200.00",
    },
    {
        "unidades": "2",
        "descripcion": "Ajuste de pulsera y limpieza ultrasonidos",
        "precio_unitario": "45",
    },
]


def cuerpo_factura(
    cliente_id: uuid.UUID,
    *,
    fecha: date | None = None,
    lineas: list[dict[str, Any]] | None = None,
    oro_inversion: bool | None = None,
) -> dict[str, Any]:
    """Sin `oro_inversion`, el cuerpo es el de antes del ajuste de cierre (por defecto `false`)."""
    cuerpo: dict[str, Any] = {
        "fecha_expedicion": (fecha or hoy()).isoformat(),
        "cliente_id": str(cliente_id),
        "lineas": LINEAS_CAPTURA if lineas is None else lineas,
    }
    if oro_inversion is not None:
        cuerpo["oro_inversion"] = oro_inversion
    return cuerpo


LINGOTE: list[dict[str, str]] = [
    {"unidades": "1", "descripcion": "Lingote de oro 100 g", "precio_unitario": "7450.00"}
]


def cabeceras(csrf: str, clave: uuid.UUID | None = None) -> dict[str, str]:
    return {"X-CSRF-Token": csrf, "Idempotency-Key": str(clave or uuid.uuid4())}


# ------------------------------------------------------------- datos confirmados (concurrencia)

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncEngine  # noqa: E402

_TABLAS_CON_TRIGGERS = (
    "correcciones_factura",
    "registros_facturacion",
    "desgloses_factura",
    "lineas_factura",
    "facturas",
    "contadores_factura",
)


async def limpiar_facturacion_confirmada(
    engine_owner: AsyncEngine, *, clientes: list[uuid.UUID], usuarios: list[uuid.UUID]
) -> None:
    """Deja la BD de test como estaba tras una prueba que confirma de verdad (solo tests).

    Las tablas de facturación son inalterables incluso para el dueño: para limpiar hay que
    desactivar sus triggers dentro de la misma transacción, lo que solo puede hacer `jb_owner`.
    """
    async with engine_owner.begin() as conn:
        for tabla in _TABLAS_CON_TRIGGERS:
            await conn.execute(text(f"ALTER TABLE {tabla} DISABLE TRIGGER USER"))
        for tabla in (*_TABLAS_CON_TRIGGERS[:5], "borradores_factura", "contadores_factura"):
            await conn.execute(text(f"DELETE FROM {tabla}"))  # noqa: S608 — nombres fijos
        for tabla in _TABLAS_CON_TRIGGERS:
            await conn.execute(text(f"ALTER TABLE {tabla} ENABLE TRIGGER USER"))
        await conn.execute(
            text(
                "UPDATE configuracion_facturacion SET iva_por_defecto = 21, emisor_iban = NULL, "
                "modalidad = NULL, emisor_nombre = NULL, emisor_nif = NULL, "
                "emisor_direccion = NULL, emisor_codigo_postal = NULL, emisor_localidad = NULL, "
                "emisor_provincia_codigo = NULL"
            )
        )
        if clientes:
            await conn.execute(text("DELETE FROM clientes WHERE id = ANY(:ids)"), {"ids": clientes})
        if usuarios:
            await conn.execute(
                text("UPDATE usuarios SET activo = false WHERE id = ANY(:ids)"), {"ids": usuarios}
            )
