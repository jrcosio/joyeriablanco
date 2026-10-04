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
    modalidad: str = "verifactu",
    estado_remision: str = "pendiente",
    xml_firmado: bytes | None = None,
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
        "modalidad": modalidad,
        "estado": estado_remision,
        "xml": xml_firmado,
        "titular": "Prueba" if xml_firmado else None,
        "certificado": huella_de_prueba("certificado") if xml_firmado else None,
    }
    await conn.execute(
        text(
            """
            INSERT INTO registros_facturacion (
                secuencia, tipo, factura_id, modalidad, id_emisor, num_serie, fecha_expedicion,
                tipo_factura, cuota_total, importe_total, primer_registro, huella_anterior,
                fecha_hora_huso_gen, huella, contenido, estado_remision, xml_firmado,
                certificado_titular, certificado_huella)
            VALUES (
                :secuencia, :tipo, :factura, :modalidad, 'B12345674', 'FAC-2026-0001',
                '29-09-2026', :tipo_factura, :cuota, :importe, :primer, :anterior,
                '2026-09-29T10:00:00+02:00', :huella, '{}'::jsonb, :estado, :xml, :titular,
                :certificado)
            """
        ),
        parametros,
    )


async def insertar_evento(
    conn: AsyncConnection,
    *,
    secuencia: int,
    huella: str,
    anterior: tuple[str, str, str] | None,
    tipo_evento: str = "01",
    fecha_hora: str = "2026-10-03T10:00:00+02:00",
) -> None:
    """Un registro de evento mínimo. `anterior` es (tipo, fecha y hora, huella) del previo."""
    await conn.execute(
        text(
            """
            INSERT INTO registros_evento (
                secuencia, tipo_evento, fecha_hora_huso_gen, primer_evento, tipo_evento_anterior,
                fecha_hora_huso_gen_anterior, huella_anterior, huella, contenido, xml_firmado,
                certificado_titular, certificado_huella)
            VALUES (
                :secuencia, :tipo, :fecha, :primer, :tipo_ant, :fecha_ant, :huella_ant, :huella,
                '{}'::jsonb, '<x/>'::bytea, 'Prueba', :certificado)
            """
        ),
        {
            "secuencia": secuencia,
            "tipo": tipo_evento,
            "fecha": fecha_hora,
            "primer": anterior is None,
            "tipo_ant": anterior[0] if anterior else None,
            "fecha_ant": anterior[1] if anterior else None,
            "huella_ant": anterior[2] if anterior else None,
            "huella": huella,
            "certificado": huella_de_prueba("certificado"),
        },
    )
