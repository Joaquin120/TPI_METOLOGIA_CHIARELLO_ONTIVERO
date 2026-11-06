"""Pruebas unitarias de seguridad y criptografía (C-04, task 2.2)."""

from datetime import timedelta
import time
import pytest

from src.api.seguridad import (
    hashear_password,
    verificar_password,
    crear_token_acceso,
    decodificar_token_acceso,
    TokenInvalidoError,
    TokenExpiradoError,
)


def test_hashing_password_y_verificacion() -> None:
    password = "mi_password_secreta_123"
    hash_resultado = hashear_password(password)

    assert hash_resultado != password
    assert "$" in hash_resultado
    assert verificar_password(password, hash_resultado) is True
    assert verificar_password("password_erronea", hash_resultado) is False


def test_hashing_genera_salts_distintos() -> None:
    password = "misma_password"
    hash_1 = hashear_password(password)
    hash_2 = hashear_password(password)

    assert hash_1 != hash_2
    assert verificar_password(password, hash_1) is True
    assert verificar_password(password, hash_2) is True


def test_crear_y_decodificar_token_exitoso() -> None:
    claims_entrada = {
        "sub": "42",
        "email": "recepcion@clinica.com",
        "tenant_id": 1,
        "rol": "Recepcionista",
        "profesional_id": None,
    }
    token = crear_token_acceso(claims_entrada, duracion=timedelta(minutes=15))
    assert isinstance(token, str)

    payload = decodificar_token_acceso(token)
    assert payload["sub"] == "42"
    assert payload["email"] == "recepcion@clinica.com"
    assert payload["tenant_id"] == 1
    assert payload["rol"] == "Recepcionista"
    assert payload["profesional_id"] is None
    assert "exp" in payload
    assert "iat" in payload


def test_decodificar_token_expirado_lanza_error() -> None:
    claims = {"sub": "1", "tenant_id": 1, "rol": "Administrador"}
    token = crear_token_acceso(claims, duracion=timedelta(seconds=-10))

    with pytest.raises(TokenExpiradoError):
        decodificar_token_acceso(token)


def test_decodificar_token_invalido_lanza_error() -> None:
    with pytest.raises(TokenInvalidoError):
        decodificar_token_acceso("token.completamente.falso")

    # Token firmado con otra clave
    claims = {"sub": "1", "tenant_id": 1, "rol": "Administrador"}
    token_otra_clave = crear_token_acceso(claims, clave_secreta="otra-clave-diferente-123456789")
    with pytest.raises(TokenInvalidoError):
        decodificar_token_acceso(token_otra_clave)

