"""Primitivas criptográficas (research R-5, R-7)."""

from argon2 import PasswordHasher

from app.core.security import (
    constant_time_equals,
    hash_password,
    needs_rehash,
    new_csrf_token,
    new_session_token,
    token_fingerprint,
    verify_password,
)


def test_hash_argon2id_verifica_y_rechaza() -> None:
    hash_ = hash_password("Cuarzo-Rubí-Esmeralda-42")

    assert hash_.startswith("$argon2id$")
    assert verify_password(hash_, "Cuarzo-Rubí-Esmeralda-42")
    assert not verify_password(hash_, "otra-contraseña-cualquiera")
    assert not verify_password("hash-corrupto", "lo-que-sea")


def test_detecta_hash_con_parametros_antiguos() -> None:
    antiguo = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1).hash("x" * 12)

    assert needs_rehash(antiguo)
    assert not needs_rehash(hash_password("x" * 12))


def test_token_de_sesion_de_256_bits_y_huella_estable() -> None:
    token = new_session_token()

    assert len(token) >= 43  # 32 bytes en base64url
    assert token != new_session_token()
    assert token_fingerprint(token) == token_fingerprint(token)
    assert len(token_fingerprint(token)) == 64
    assert token not in token_fingerprint(token)
    assert new_csrf_token() != new_csrf_token()


def test_comparacion_en_tiempo_constante() -> None:
    assert constant_time_equals("abc", "abc")
    assert not constant_time_equals("abc", "abd")
    assert not constant_time_equals("abc", "")
