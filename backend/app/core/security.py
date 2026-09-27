"""Primitivas criptográficas: Argon2id y tokens de sesión y CSRF (research R-5 a R-7)."""

import hashlib
import hmac
import secrets
from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()  # Argon2id, perfil RFC 9106 de baja memoria (t=3, m=64 MiB, p=4)


def hash_password(contrasena: str) -> str:
    return _hasher.hash(contrasena)


def verify_password(hash_: str, contrasena: str) -> bool:
    try:
        return _hasher.verify(hash_, contrasena)
    except (VerificationError, InvalidHashError):  # VerifyMismatchError hereda de VerificationError
        return False


def needs_rehash(hash_: str) -> bool:
    try:
        return _hasher.check_needs_rehash(hash_)
    except InvalidHashError:
        return True


@lru_cache(maxsize=1)
def dummy_hash() -> str:
    """Hash ficticio para igualar el tiempo de respuesta cuando el usuario no existe (FR-007)."""
    return _hasher.hash(secrets.token_urlsafe(16))


def new_session_token() -> str:
    """256 bits aleatorios en base64url."""
    return secrets.token_urlsafe(32)


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def token_fingerprint(token: str) -> str:
    """Huella SHA-256 del token: es lo único que se guarda en la BD (FR-010)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))
