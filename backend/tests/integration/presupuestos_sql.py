"""Utilidades SQL para los tests de presupuestos: inserciones mínimas válidas por debajo del ORM.

Sirven para probar las garantías de la BD (triggers, privilegios y unicidades) de la 0008 sin
depender de los servicios (005, data-model).
"""

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


async def insertar_presupuesto(
    conn: AsyncConnection, usuario: uuid.UUID, cliente: uuid.UUID, numero: int, **extra: Any
) -> uuid.UUID:
    parametros: dict[str, Any] = {
        "numero": numero,
        "num_serie": f"PRE-2026-{numero:04d}",
        "cliente": cliente,
        "usuario": usuario,
        "valido_hasta": extra.get("valido_hasta", "2026-10-31"),
    }
    presupuesto = (
        await conn.execute(
            text(
                """
                INSERT INTO presupuestos (
                    serie, anio, numero, num_serie, fecha, valido_hasta, emisor_nif,
                    emisor_nombre, emisor_direccion, emisor_codigo_postal, emisor_localidad,
                    cliente_id, dest_nombre, dest_identificacion_pais, dest_identificacion_tipo,
                    dest_identificacion_numero, dest_pais, oro_inversion, base_total,
                    cuota_total, importe_total, emitido_por_id)
                VALUES (
                    'PRE', 2026, :numero, :num_serie, DATE '2026-10-01',
                    CAST(:valido_hasta AS date), 'B12345674', 'Joyería', 'Calle 1', '28001',
                    'Madrid', :cliente, 'Cliente SQL', 'ES', '03', 'P1', 'ES', false, 100, 21,
                    121, :usuario)
                RETURNING id
                """
            ),
            parametros,
        )
    ).scalar_one()
    return uuid.UUID(str(presupuesto))


async def insertar_contenido(conn: AsyncConnection, presupuesto: uuid.UUID) -> None:
    await conn.execute(
        text(
            "INSERT INTO lineas_presupuesto (presupuesto_id, orden, unidades, descripcion, "
            "precio_unitario, tipo_iva, importe) VALUES (:p, 1, 1, 'Anillo', 100, 21, 100)"
        ),
        {"p": presupuesto},
    )
    await conn.execute(
        text(
            "INSERT INTO desgloses_presupuesto (presupuesto_id, orden, tipo_iva, base, cuota) "
            "VALUES (:p, 1, 21, 100, 21)"
        ),
        {"p": presupuesto},
    )


async def insertar_cierre(
    conn: AsyncConnection,
    presupuesto: uuid.UUID,
    usuario: uuid.UUID,
    tipo: str = "anulacion",
    **extra: Any,
) -> None:
    parametros: dict[str, Any] = {
        "p": presupuesto,
        "tipo": tipo,
        "u": usuario,
        "motivo": extra.get("motivo_texto", None if tipo == "conversion" else "Rechazado"),
        "nuevo": extra.get("presupuesto_nuevo_id"),
        "factura": extra.get("factura_id"),
        "clave": extra.get("clave", uuid.uuid4() if tipo == "anulacion" else None),
        "operacion": "anular" if tipo == "anulacion" else None,
    }
    await conn.execute(
        text(
            "INSERT INTO cierres_presupuesto (presupuesto_id, tipo, motivo_texto, "
            "presupuesto_nuevo_id, factura_id, creado_por_id, clave_idempotencia, "
            "operacion_idempotencia) VALUES (:p, :tipo, :motivo, :nuevo, :factura, :u, :clave, "
            ":operacion)"
        ),
        parametros,
    )


async def insertar_borrador_factura(
    conn: AsyncConnection, usuario: uuid.UUID, cliente: uuid.UUID, presupuesto: uuid.UUID | None
) -> uuid.UUID:
    borrador = (
        await conn.execute(
            text(
                "INSERT INTO borradores_factura (cliente_id, fecha_expedicion, tipo_iva_previsto, "
                "creado_por_id, actualizado_por_id, presupuesto_id) "
                "VALUES (:c, DATE '2026-10-02', 21, :u, :u, :p) RETURNING id"
            ),
            {"c": cliente, "u": usuario, "p": presupuesto},
        )
    ).scalar_one()
    return uuid.UUID(str(borrador))
