"""Funciones criptográficas de seguridad, hashing y tokens JWT (C-04, task 2.1)."""

from datetime import datetime, timezone, timedelta
import hashlib
import hmac
import os
from typing import Any
import jwt

from src.infrastructure.config import clave_secreta_jwt, expiracion_token_minutos

ALGORITMO_JWT = "HS256"
ITERACIONES_PBKDF2 = 100_000


class TokenInvalidoError(Exception):
    """El token JWT es inválido, está corrupto o la firma no coincide."""


class TokenExpiradoError(TokenInvalidoError):
    """El token JWT ha expirado en su validez temporal."""


def hashear_password(
    password: str,
    salt: bytes | None = None,
    iteraciones: int = ITERACIONES_PBKDF2,
) -> str:
    """Calcula un hash criptográfico PBKDF2-HMAC-SHA256 con salt aleatorio.

    Formato resultante: `salt_hex$hash_hex`.
    """
    if salt is None:
        salt = os.urandom(16)
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iteraciones,
    )
    return f"{salt.hex()}${hash_bytes.hex()}"


def verificar_password(password: str, hash_almacenado: str) -> bool:
    """Verifica si la contraseña coincide con el hash almacenado."""
    try:
        salt_hex, hash_hex = hash_almacenado.split("$")
        salt = bytes.fromhex(salt_hex)
        hash_esperado = bytes.fromhex(hash_hex)
    except (ValueError, TypeError):
        return False

    hash_calculado = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        ITERACIONES_PBKDF2,
    )
    return hmac.compare_digest(hash_calculado, hash_esperado)


def crear_token_acceso(
    claims: dict[str, Any],
    duracion: timedelta | None = None,
    clave_secreta: str | None = None,
) -> str:
    """Genera un token JWT firmado con HS256 incluyendo claims y fechas iat/exp."""
    ahora = datetime.now(timezone.utc)
    if duracion is None:
        duracion = timedelta(minutes=expiracion_token_minutos())
    expiracion = ahora + duracion

    payload = dict(claims)
    payload["iat"] = int(ahora.timestamp())
    payload["exp"] = int(expiracion.timestamp())

    clave = clave_secreta if clave_secreta is not None else clave_secreta_jwt()
    return jwt.encode(payload, clave, algorithm=ALGORITMO_JWT)


def decodificar_token_acceso(
    token: str,
    clave_secreta: str | None = None,
) -> dict[str, Any]:
    """Decodifica y valida firma y expiración de un token JWT HS256."""
    clave = clave_secreta if clave_secreta is not None else clave_secreta_jwt()
    try:
        return jwt.decode(token, clave, algorithms=[ALGORITMO_JWT])
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiradoError("El token ha expirado") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenInvalidoError("Token inválido") from exc

