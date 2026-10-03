"""Certificado de firma: estado y motivos de no utilizable (004, research R-6; FR-002 a FR-004).

Cada motivo se reproduce con un PKCS#12 generado por `generar_pkcs12`. La validez se comprueba en
la fecha que se pasa (la de generación del registro, F-14 §3), no en la de hoy.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import SecretStr

from app.core.config import Entorno, Settings
from app.domain.tipos import MotivoNoUtilizable
from app.services import certificado
from app.services.certificado import CertificadoNoUtilizable
from tests.certificados import CONTRASENA_PRUEBAS, escribir_pkcs12

AHORA = datetime.now(UTC)


def _ajustes(ruta: Path | None, contrasena: str = CONTRASENA_PRUEBAS, **extra: Any) -> Settings:
    return Settings.model_validate(
        {
            "entorno": Entorno.TEST,
            "certificado_ruta": ruta,
            "certificado_contrasena": SecretStr(contrasena),
            **extra,
        }
    )


def _produccion(ruta: Path) -> Settings:
    return Settings.model_validate(
        {
            "entorno": Entorno.PRODUCCION,
            "origen_permitido": "https://gestion.example.com",
            "aeat_entorno": "pruebas",
            "sif_productor_nombre": "Productora, S.L.",
            "sif_productor_nif": "12345678Z",
            "sif_productor_direccion": "Calle Mayor 1, 28001 Madrid",
            "sif_declaracion_fecha": "2026-10-03",
            "sif_declaracion_lugar": "Madrid (España)",
            "certificado_ruta": ruta,
            "certificado_contrasena": SecretStr(CONTRASENA_PRUEBAS),
        }
    )


def test_un_certificado_valido_es_utilizable_y_muestra_sus_datos(tmp_path: Path) -> None:
    ajustes = _ajustes(
        escribir_pkcs12(tmp_path / "c.p12", titular="JOYERIA BLANCO", nif="B12345674")
    )

    estado = certificado.estado(ajustes=ajustes)
    firma = certificado.utilizable(ajustes=ajustes)

    assert estado.utilizable
    assert estado.motivo is None
    assert estado.titular == "JOYERIA BLANCO"
    assert estado.identificacion == "B12345674"  # sin el prefijo IDCES-
    assert estado.emisor == "JOYERIA BLANCO"  # autofirmado
    assert estado.dias_restantes in {363, 364}
    assert not estado.caduca_pronto
    assert firma.huella == firma.huella.upper()
    assert len(firma.huella) == 64


@pytest.mark.parametrize(
    ("opciones", "motivo"),
    [
        ({"desde": AHORA - timedelta(days=400), "dias": 365}, MotivoNoUtilizable.CADUCADO),
        ({"desde": AHORA + timedelta(days=10)}, MotivoNoUtilizable.AUN_NO_VALIDO),
        ({"con_clave": False}, MotivoNoUtilizable.SIN_CLAVE_PRIVADA),
        ({"firma": False}, MotivoNoUtilizable.NO_APTO_PARA_FIRMAR),
    ],
    ids=["caducado", "aun-no-valido", "sin-clave", "sin-uso-de-firma"],
)
def test_cada_motivo_de_no_utilizable(
    tmp_path: Path, opciones: dict[str, Any], motivo: MotivoNoUtilizable
) -> None:
    ajustes = _ajustes(escribir_pkcs12(tmp_path / "c.p12", **opciones))

    with pytest.raises(CertificadoNoUtilizable) as info:
        certificado.utilizable(ajustes=ajustes)

    assert info.value.motivo is motivo
    assert certificado.estado(ajustes=ajustes).motivo is motivo


def test_sin_ruta_o_sin_fichero_no_esta_instalado(tmp_path: Path) -> None:
    sin_ruta = Settings(entorno=Entorno.TEST, certificado_ruta=None)  # sin el de la sesión

    assert certificado.estado(ajustes=sin_ruta).motivo is MotivoNoUtilizable.NO_INSTALADO
    assert (
        certificado.estado(ajustes=_ajustes(tmp_path / "no-existe.p12")).motivo
        is MotivoNoUtilizable.NO_INSTALADO
    )


def test_con_la_contrasena_erronea_o_un_fichero_danado_es_ilegible(tmp_path: Path) -> None:
    ruta = escribir_pkcs12(tmp_path / "c.p12")
    danado = tmp_path / "danado.p12"
    danado.write_bytes(b"no es un pkcs12")

    assert certificado.estado(ajustes=_ajustes(ruta, "otra")).motivo is MotivoNoUtilizable.ILEGIBLE
    assert certificado.estado(ajustes=_ajustes(danado)).motivo is MotivoNoUtilizable.ILEGIBLE


@pytest.mark.parametrize("marca_pruebas", [True, False], ids=["con-marca", "autofirmado"])
def test_un_certificado_de_pruebas_no_vale_en_produccion(
    tmp_path: Path, marca_pruebas: bool
) -> None:
    ruta = escribir_pkcs12(tmp_path / "c.p12", marca_pruebas=marca_pruebas)

    with pytest.raises(CertificadoNoUtilizable) as info:
        certificado.utilizable(ajustes=_produccion(ruta))

    assert info.value.motivo is MotivoNoUtilizable.DE_PRUEBAS_EN_PRODUCCION
    assert certificado.utilizable(ajustes=_ajustes(ruta))  # fuera de producción, sí


def test_avisa_desde_30_dias_antes_de_caducar(tmp_path: Path) -> None:
    ajustes = _ajustes(
        escribir_pkcs12(tmp_path / "c.p12", desde=AHORA - timedelta(days=340), dias=365)
    )

    estado = certificado.estado(ajustes=ajustes)

    assert estado.utilizable
    assert estado.caduca_pronto
    assert estado.dias_restantes in {24, 25}


def test_la_validez_se_comprueba_en_la_fecha_del_registro(tmp_path: Path) -> None:
    ajustes = _ajustes(escribir_pkcs12(tmp_path / "c.p12", desde=AHORA - timedelta(days=1)))

    assert certificado.utilizable(AHORA, ajustes=ajustes)
    with pytest.raises(CertificadoNoUtilizable) as antes:
        certificado.utilizable(AHORA - timedelta(days=2), ajustes=ajustes)
    assert antes.value.motivo is MotivoNoUtilizable.AUN_NO_VALIDO
    with pytest.raises(CertificadoNoUtilizable) as despues:
        certificado.utilizable(AHORA + timedelta(days=400), ajustes=ajustes)
    assert despues.value.motivo is MotivoNoUtilizable.CADUCADO


def test_si_cambia_el_fichero_se_vuelve_a_leer(tmp_path: Path) -> None:
    ruta = escribir_pkcs12(tmp_path / "c.p12", titular="PRIMERO")
    ajustes = _ajustes(ruta)
    assert certificado.estado(ajustes=ajustes).titular == "PRIMERO"

    escribir_pkcs12(ruta, titular="EL SEGUNDO CERTIFICADO")

    assert certificado.estado(ajustes=ajustes).titular == "EL SEGUNDO CERTIFICADO"


def test_el_estado_nunca_contiene_la_contrasena_ni_la_clave(tmp_path: Path) -> None:
    ajustes = _ajustes(escribir_pkcs12(tmp_path / "c.p12"))

    texto = repr(certificado.estado(ajustes=ajustes))

    assert CONTRASENA_PRUEBAS not in texto
    assert "PRIVATE" not in texto
    assert "clave" not in texto
