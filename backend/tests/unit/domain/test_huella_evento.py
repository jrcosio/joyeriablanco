"""⚖️ Test obligatorio (constitución VII, 2.4.0): huella encadenada de los registros de evento.

F-2, §3.c (v0.1.2, pp. 5–7): nueve campos en orden, con el NIF del sistema y el del obligado, el
`ID` vacío cuando se informa el NIF, `HuellaEvento=` vacío en el primero y SHA-256 en hexadecimal
mayúsculas. F-2 no trae vectores de eventos: la cadena esperada se escribe aquí literalmente y la
huella se calcula aparte con `hashlib` (research R-7).
"""

from dataclasses import replace
from hashlib import sha256

from app.domain.huella import CamposHuellaEvento, compute_huella

PRIMERO = CamposHuellaEvento(
    nif_sistema="B12345674",
    id_otro_sistema="",
    id_sistema="JB",
    version="0.4.0",
    numero_instalacion="1",
    nif_obligado="89890001K",
    tipo_evento="01",
    huella_anterior="",
    fecha_hora_huso_gen="2026-10-03T09:00:00+02:00",
)
CADENA_PRIMERO = (
    "NIF=B12345674&ID=&IdSistemaInformatico=JB&Version=0.4.0&NumeroInstalacion=1"
    "&NIF=89890001K&TipoEvento=01&HuellaEvento=&FechaHoraHusoGenEvento=2026-10-03T09:00:00+02:00"
)


def test_la_cadena_sigue_el_orden_de_f2_con_los_dos_nif() -> None:
    assert PRIMERO.cadena() == CADENA_PRIMERO


def test_la_huella_es_sha256_en_mayusculas() -> None:
    huella = compute_huella(PRIMERO.cadena())

    assert huella == sha256(CADENA_PRIMERO.encode("utf-8")).hexdigest().upper()
    assert len(huella) == 64
    assert huella == huella.upper()


def test_el_siguiente_encadena_con_la_huella_del_anterior() -> None:
    anterior = compute_huella(PRIMERO.cadena())
    siguiente = replace(
        PRIMERO,
        tipo_evento="10",
        huella_anterior=anterior,
        fecha_hora_huso_gen="2026-10-03T15:00:00+02:00",
    )

    assert f"&TipoEvento=10&HuellaEvento={anterior}&FechaHoraHusoGenEvento=" in siguiente.cadena()
    assert compute_huella(siguiente.cadena()) != anterior


def test_los_espacios_extremos_se_recortan() -> None:
    con_espacios = replace(PRIMERO, numero_instalacion="  1  ", version=" 0.4.0")

    assert con_espacios.cadena() == CADENA_PRIMERO
