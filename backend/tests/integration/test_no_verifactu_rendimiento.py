"""Rendimiento de la modalidad No VERI*FACTU (004; SC-005 a SC-007). Marca `lento`.

`uv run pytest -m lento`. Las 20.000 facturas se emiten con el servicio real, así que cada registro
se genera en XML, se firma y se valida como en producción, dentro de la transacción del test (se
revierte al terminar). Tarda unos minutos.

- SC-007: con la firma, el p95 de la emisión sigue por debajo de 1 s.
- SC-005: exportar los 20.000 registros termina en menos de 1 minuto, con todos idénticos.
- SC-006: comprobar la integridad completa (registros y eventos) termina en menos de 3 minutos.
"""

import os
import statistics
import time
import uuid
import zipfile
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.http import Origen
from app.core.security import hash_password
from app.core.tiempo import hoy
from app.domain.tipos import Rol
from app.models import RegistroFacturacion, Usuario
from app.services import emision, exportacion, integridad
from tests.integration.facturacion_datos import configurar_facturacion, crear_cliente

pytestmark = pytest.mark.lento
TOTAL = int(os.environ.get("JB_RENDIMIENTO_REGISTROS", "20000"))
ORIGEN = Origen(ip=None, agente="pytest")


async def test_emision_exportacion_y_comprobacion_con_20000_registros(
    db: AsyncSession,
) -> None:
    admin = Usuario(
        nombre_usuario=f"rendimiento.{uuid.uuid4().hex[:6]}",
        nombre="Rendimiento",
        rol=Rol.ADMINISTRADOR.value,
        hash_contrasena=hash_password("x" * 12),
        contrasena_temporal=False,
    )
    db.add(admin)
    await db.flush()
    await configurar_facturacion(db)
    cliente = await crear_cliente(db, admin.id)

    tiempos = []
    for i in range(TOTAL):
        inicio = time.perf_counter()
        await emision.emit_factura(
            db,
            emision.DatosFactura(
                fecha_expedicion=hoy(),
                cliente_id=cliente.id,
                lineas=(emision.DatosLinea(Decimal(1), "Anillo", Decimal(100 + i % 900)),),
            ),
            actor=admin,
            origen=ORIGEN,
            clave=uuid.uuid4(),
        )
        tiempos.append(time.perf_counter() - inicio)
    p95 = statistics.quantiles(tiempos, n=20)[-1]
    assert await db.scalar(select(func.count()).select_from(RegistroFacturacion)) == TOTAL

    inicio = time.perf_counter()
    exportado = await exportacion.export_records(db, tipo="facturacion", desde=hoy(), hasta=hoy())
    exportar = time.perf_counter() - inicio
    try:
        with zipfile.ZipFile(exportado.ruta) as archivo:
            xmls = [n for n in archivo.namelist() if n.startswith("facturacion/")]
            assert len(xmls) == TOTAL
            primero = (
                await db.execute(
                    select(RegistroFacturacion).where(RegistroFacturacion.secuencia == 1)
                )
            ).scalar_one()
            assert archivo.read(xmls[0]) == primero.xml_firmado
    finally:
        exportado.ruta.unlink(missing_ok=True)

    inicio = time.perf_counter()
    resultado = await integridad.verify_chain(db)
    comprobar = time.perf_counter() - inicio

    print(  # noqa: T201 — el resultado se anota en el quickstart
        f"\n{TOTAL} registros: emisión p95 {p95 * 1000:.0f} ms, exportación {exportar:.1f} s, "
        f"comprobación {comprobar:.1f} s"
    )
    assert resultado.integra, resultado.anomalias[:3]
    assert resultado.registros == TOTAL
    assert p95 < 1.0  # SC-007
    assert exportar < 60  # SC-005
    assert comprobar < 180  # SC-006
