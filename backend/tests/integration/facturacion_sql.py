"""Utilidades SQL para los tests de facturación: inserciones mínimas válidas por debajo del ORM.

Sirven para probar las garantías de la BD (triggers y privilegios) sin depender de los servicios.
"""

import hashlib
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

PRIVILEGIO_INSUFICIENTE = "42501"


async def insertar_usuario_y_cliente(conn: AsyncConnection) -> tuple[uuid.UUID, uuid.UUID]:
    sufijo = uuid.uuid4().hex[:8]
    usuario: uuid.UUID = (
        await conn.execute(
            text(
                "INSERT INTO usuarios (nombre_usuario, nombre, rol, hash_contrasena) "
                "VALUES (:u, 'Prueba', 'administrador', 'x') RETURNING id"
            ),
            {"u": f"sql.{sufijo}"},
        )
    ).scalar_one()
    cliente: uuid.UUID = (
        await conn.execute(
            text(
                "INSERT INTO clientes (tipo, nombre, identificacion_tipo, identificacion_numero, "
                "creado_por_id, actualizado_por_id) "
                "VALUES ('particular', 'Cliente SQL', '03', :n, :u, :u) RETURNING id"
            ),
            {"n": f"P{sufijo}", "u": usuario},
        )
    ).scalar_one()
    return usuario, cliente


async def insertar_factura(
    conn: AsyncConnection, usuario: uuid.UUID, cliente: uuid.UUID, numero: int
) -> uuid.UUID:
    return uuid.UUID(
        str(
            (
                await conn.execute(
                    text(
                        """
                        INSERT INTO facturas (
                            serie, anio, numero, num_serie, tipo_factura, fecha_expedicion,
                            descripcion_operacion, emisor_nif, emisor_nombre, emisor_direccion,
                            emisor_codigo_postal, emisor_localidad, cliente_id, dest_nombre,
                            dest_identificacion_pais, dest_identificacion_tipo,
                            dest_identificacion_numero, dest_direccion, dest_codigo_postal,
                            dest_localidad, dest_pais, clave_regimen, modalidad, base_total,
                            cuota_total, importe_total, emitida_por_id)
                        VALUES (
                            'FAC', 2026, :numero, :num_serie, 'F1', DATE '2026-09-29',
                            'Anillo', 'B12345674', 'Joyería', 'Calle 1', '28001', 'Madrid',
                            :cliente, 'Cliente SQL', 'ES', '03', 'P1', 'Calle 2', '28002',
                            'Madrid', 'ES', '01', 'verifactu', 100, 21, 121, :usuario)
                        RETURNING id
                        """
                    ),
                    {
                        "numero": numero,
                        "num_serie": f"FAC-2026-{numero:04d}",
                        "cliente": cliente,
                        "usuario": usuario,
                    },
                )
            ).scalar_one()
        )
    )


def huella_de_prueba(semilla: str) -> str:
    return hashlib.sha256(semilla.encode()).hexdigest().upper()


async def insertar_registro(
    conn: AsyncConnection,
    factura: uuid.UUID,
    *,
    secuencia: int,
    huella: str,
    huella_anterior: str | None,
    tipo: str = "alta",
) -> None:
    alta = tipo == "alta"
    parametros: dict[str, Any] = {
        "secuencia": secuencia,
        "tipo": tipo,
        "factura": factura,
        "tipo_factura": "F1" if alta else None,
        "cuota": 21 if alta else None,
        "importe": 121 if alta else None,
        "primer": huella_anterior is None,
        "anterior": huella_anterior,
        "huella": huella,
    }
    await conn.execute(
        text(
            """
            INSERT INTO registros_facturacion (
                secuencia, tipo, factura_id, modalidad, id_emisor, num_serie, fecha_expedicion,
                tipo_factura, cuota_total, importe_total, primer_registro, huella_anterior,
                fecha_hora_huso_gen, huella, contenido)
            VALUES (
                :secuencia, :tipo, :factura, 'verifactu', 'B12345674', 'FAC-2026-0001',
                '29-09-2026', :tipo_factura, :cuota, :importe, :primer, :anterior,
                '2026-09-29T10:00:00+02:00', :huella, '{}'::jsonb)
            """
        ),
        parametros,
    )
