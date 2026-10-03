"""Certificados de prueba para los tests (004, research R-6).

Se generan con el mismo `generar_pkcs12` que usa `joyeria generar-certificado-pruebas`, con las
opciones que reproducen cada motivo de «no utilizable».
"""

from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12

from app.services.certificado import CertificadoFirma, generar_pkcs12

CONTRASENA_PRUEBAS = "pruebas-tests"


def escribir_pkcs12(
    destino: Path, *, contrasena: str = CONTRASENA_PRUEBAS, **opciones: Any
) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(generar_pkcs12(contrasena, **opciones))
    return destino


def certificado_firma(**opciones: Any) -> CertificadoFirma:
    """Un certificado utilizable en memoria, sin pasar por los ajustes."""
    clave, certificado, adicionales = pkcs12.load_key_and_certificates(
        generar_pkcs12(CONTRASENA_PRUEBAS, **opciones), CONTRASENA_PRUEBAS.encode()
    )
    assert isinstance(clave, rsa.RSAPrivateKey)
    assert certificado is not None
    return CertificadoFirma(clave=clave, certificado=certificado, adicionales=tuple(adicionales))
