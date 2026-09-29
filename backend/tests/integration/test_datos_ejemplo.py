"""Datos de ejemplo para desarrollo y E2E (US7; FR-045)."""

from collections import Counter
from datetime import timedelta
from itertools import pairwise

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import SinPermiso
from app.core.security import verify_password
from app.core.tiempo import hoy
from app.domain.identificacion import validate_identificacion
from app.domain.tipos import Rol, TipoIdentificacion
from app.models import Cliente, Factura, Usuario
from app.models.borrador_factura import BorradorFactura
from app.repositories import registros
from app.services import cadena, datos_ejemplo, integridad
from app.services.configuracion_facturacion import get_config


async def test_carga_clientes_y_usuarios_validos(db: AsyncSession) -> None:
    resumen = await datos_ejemplo.cargar(db, clientes=40, contrasena_demo="Demo-Zafiro-2026-xyz")

    assert resumen.clientes_creados == 40
    usuarios = {u.nombre_usuario: u for u in (await db.execute(select(Usuario))).scalars()}
    assert usuarios["admin.demo"].rol == Rol.ADMINISTRADOR
    assert usuarios["empleado.demo"].rol == Rol.EMPLEADO
    assert usuarios["vendedor.demo"].rol == Rol.EMPLEADO
    assert usuarios["admin.demo"].contrasena_temporal is False
    assert verify_password(usuarios["admin.demo"].hash_contrasena, "Demo-Zafiro-2026-xyz")

    clientes = list((await db.execute(select(Cliente))).unique().scalars())
    assert len(clientes) == 40
    for cliente in clientes:
        assert cliente.observaciones is not None
        assert cliente.observaciones.startswith(datos_ejemplo.MARCADOR)
        canonico, errores = validate_identificacion(
            cliente.identificacion_pais,
            TipoIdentificacion(cliente.identificacion_tipo),
            cliente.identificacion_numero,
        )
        assert errores == [], (cliente.nombre, cliente.identificacion_numero)
        assert canonico == cliente.identificacion_numero
    assert any(not c.activo for c in clientes)
    assert any(c.tipo == "empresa" for c in clientes)
    assert any(c.identificacion_pais != "ES" for c in clientes)


async def test_emite_facturas_encadenadas_con_la_configuracion_demo(db: AsyncSession) -> None:
    """R-16: las facturas y sus correcciones pasan por los servicios, así que la cadena queda
    íntegra y cada estado sale de las correcciones."""
    resumen = await datos_ejemplo.cargar(db, clientes=40, facturas=50)

    assert resumen.facturas_emitidas == 50
    estado = await get_config(db)
    assert estado.faltan == []
    assert estado.config.modalidad == "verifactu"
    assert estado.config.emisor_nombre == "Joyería Blanco (demo)"

    todas = list(
        (
            await db.execute(select(Factura).order_by(Factura.serie, Factura.anio, Factura.numero))
        ).scalars()
    )
    ordinarias = [f for f in todas if f.serie == "FAC"]
    assert len(ordinarias) == 51  # las 50 y la que sustituye a la reemitida
    assert len([f for f in todas if f.serie == "REC"]) == 3
    hoy_madrid = hoy()
    for previa, siguiente in pairwise(ordinarias):
        if previa.anio == siguiente.anio:
            assert siguiente.numero == previa.numero + 1
            assert siguiente.fecha_expedicion >= previa.fecha_expedicion
    for factura in ordinarias:
        assert hoy_madrid - timedelta(days=182) < factura.fecha_expedicion <= hoy_madrid
        assert factura.importe_total > 0
        assert factura.dest_direccion is not None

    # T069: anulación, reemisión, R4, devolución total R1 y rectificativa anulada.
    assert resumen.correcciones == 6
    estados = Counter([str(await db.scalar(select(func.estado_factura(f.id)))) for f in todas])
    assert estados["anulada"] == 3  # la anulada, la reemitida y la rectificativa anulada
    assert estados["rectificada"] == 2
    assert {f.tipo_factura for f in todas if f.serie == "REC"} == {"R1", "R4"}

    cola = await registros.list_in_order(db)
    # 50 altas + anulación + (anulación + alta) + 3 altas REC + anulación de la REC.
    assert [r.secuencia for r in cola] == list(range(1, 58))
    for anterior, actual in pairwise(cola):
        assert actual.huella_anterior == anterior.huella
    for registro in cola:
        assert cadena.recompute_huella(registro) == registro.huella
    comprobacion = await integridad.verify_chain(db)  # FR-031 sobre una cadena con correcciones
    assert comprobacion.integra, comprobacion.discrepancia
    assert comprobacion.registros == 57

    # Cinco borradores de hoy, el primero sin cliente, con sus totales previstos (T061).
    assert resumen.borradores_creados == 5
    borradores = list((await db.execute(select(BorradorFactura))).unique().scalars())
    assert len(borradores) == 5
    assert sum(b.cliente_id is None for b in borradores) >= 1
    assert all(b.lineas and b.total_previsto > 0 for b in borradores)


async def test_es_idempotente(db: AsyncSession) -> None:
    await datos_ejemplo.cargar(db, clientes=10)
    segunda = await datos_ejemplo.cargar(db, clientes=10)

    assert segunda.clientes_creados == 0
    assert segunda.ya_cargados is True
    total = await db.scalar(select(func.count()).select_from(Cliente))
    assert total == 10


async def test_sin_contrasena_demo_los_usuarios_reciben_temporales(db: AsyncSession) -> None:
    resumen = await datos_ejemplo.cargar(db, clientes=1)

    assert set(resumen.contrasenas_temporales) == {"admin.demo", "empleado.demo", "vendedor.demo"}
    admin = await db.scalar(select(Usuario).where(Usuario.nombre_usuario == "admin.demo"))
    assert admin is not None
    assert admin.contrasena_temporal is True


async def test_se_niega_en_produccion(db: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENTORNO", "produccion")
    monkeypatch.setenv("SIF_PRODUCTOR_NOMBRE", "Productora de pruebas, S.L.")
    monkeypatch.setenv("SIF_PRODUCTOR_NIF", "12345678Z")
    monkeypatch.setenv("ORIGEN_PERMITIDO", "https://joyeria.example.com")
    get_settings.cache_clear()
    try:
        with pytest.raises(SinPermiso):
            await datos_ejemplo.cargar(db, clientes=1)
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
