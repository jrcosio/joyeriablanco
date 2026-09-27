"""Datos de ejemplo para desarrollo y E2E (US7; FR-045)."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import SinPermiso
from app.core.security import verify_password
from app.domain.identificacion import validate_identificacion
from app.domain.tipos import Rol, TipoIdentificacion
from app.models import Cliente, Usuario
from app.services import datos_ejemplo


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
    monkeypatch.setenv("ORIGEN_PERMITIDO", "https://joyeria.example.com")
    get_settings.cache_clear()
    try:
        with pytest.raises(SinPermiso):
            await datos_ejemplo.cargar(db, clientes=1)
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
