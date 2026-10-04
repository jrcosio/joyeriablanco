"""US2 de 004 — Consulta del registro de eventos (FR-016, FR-020; RRSIF, art. 8.3; Orden, 7.h)."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tiempo import hoy
from app.domain.tipos import Rol, TipoEventoSif
from app.services import eventos_sif
from app.services.eventos_sif import NuevoEvento
from tests.conftest import CrearUsuario, IniciarSesion

URL = "/api/v1/registro-fiscal/eventos"


@pytest.fixture
async def admin(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> str:
    await crear_usuario("admin.eventos", rol=Rol.ADMINISTRADOR)
    return await iniciar_sesion(client, "admin.eventos")


async def _tres_eventos(db: AsyncSession) -> None:
    await eventos_sif.record_evento(db, NuevoEvento(TipoEventoSif.INICIO))
    await eventos_sif.record_resumen(db)
    await eventos_sif.record_evento(
        db, NuevoEvento(TipoEventoSif.FIN, otros_datos=eventos_sif.TEXTO_PARADA)
    )


@pytest.mark.usefixtures("admin")
async def test_la_lista_va_del_mas_reciente_al_mas_antiguo(
    client: AsyncClient, db: AsyncSession
) -> None:
    await _tres_eventos(db)

    pagina = (await client.get(URL)).json()

    assert pagina["total"] == 3
    assert [e["tipo_evento"] for e in pagina["elementos"]] == ["02", "10", "01"]
    fin, resumen, inicio = pagina["elementos"]
    assert fin["resumen"] == eventos_sif.TEXTO_PARADA
    assert resumen["resumen"] == "1 eventos, 0 altas y 0 anulaciones"
    assert inicio["resumen"] is None
    assert inicio["certificado_titular"] == "JOYERIA BLANCO (PRUEBAS)"
    assert set(inicio) == {
        "secuencia",
        "tipo_evento",
        "fecha_hora_huso_gen",
        "huella",
        "certificado_titular",
        "resumen",
    }


@pytest.mark.usefixtures("admin")
async def test_filtros_por_tipo_y_por_dias_y_paginacion(
    client: AsyncClient, db: AsyncSession
) -> None:
    await _tres_eventos(db)

    por_tipo = (await client.get(URL, params={"tipo": "10"})).json()
    de_hoy = (await client.get(URL, params={"desde": hoy().isoformat()})).json()
    futuro = (await client.get(URL, params={"desde": "2099-01-01"})).json()
    hasta_ayer = (await client.get(URL, params={"hasta": "2024-12-31"})).json()
    segunda = (await client.get(URL, params={"pagina": 2, "tamano": 2})).json()
    no_valido = await client.get(URL, params={"tipo": "07"})

    assert [e["tipo_evento"] for e in por_tipo["elementos"]] == ["10"]
    assert de_hoy["total"] == 3
    assert futuro["total"] == 0
    assert hasta_ayer["total"] == 0
    assert [e["tipo_evento"] for e in segunda["elementos"]] == ["01"]
    assert segunda["total"] == 3
    assert no_valido.status_code == 422  # el 07 no se genera (contrato)


@pytest.mark.usefixtures("admin")
async def test_el_detalle_comprueba_huella_y_firma_y_salta_al_anterior_y_al_siguiente(
    client: AsyncClient, db: AsyncSession
) -> None:
    await _tres_eventos(db)

    primero = (await client.get(f"{URL}/1")).json()
    segundo = (await client.get(f"{URL}/2")).json()
    ultimo = (await client.get(f"{URL}/3")).json()
    inexistente = await client.get(f"{URL}/99")

    assert segundo["huella_correcta"] is True
    assert segundo["firma_correcta"] is True
    assert segundo["anterior"] == {
        "secuencia": 1,
        "encadenamiento_correcto": True,
        "fechas_en_orden": True,
    }
    assert segundo["siguiente"] == {
        "secuencia": 3,
        "encadenamiento_correcto": True,
        "fechas_en_orden": True,
    }
    assert segundo["datos"]["ResumenEventos"]["TipoEvento"] == [
        {"TipoEvento": "01", "NumeroDeEventos": "1"}
    ]
    assert primero["anterior"] is None
    assert ultimo["siguiente"] is None
    assert ultimo["datos"] == {"OtrosDatosEvento": eventos_sif.TEXTO_PARADA}
    assert inexistente.status_code == 404


async def test_un_empleado_no_ve_el_registro_de_eventos(
    client: AsyncClient, crear_usuario: CrearUsuario, iniciar_sesion: IniciarSesion
) -> None:
    await crear_usuario("empleado.eventos")
    await iniciar_sesion(client, "empleado.eventos")

    lista = await client.get(URL)
    detalle = await client.get(f"{URL}/1")

    assert [lista.status_code, detalle.status_code] == [403, 403]
