"""Envelope de error estable y handlers de excepción (design D6).

Forma única de salida:

    {"error": {"code": "...", "message": "..."}}

El `message` conserva el texto de la excepción de dominio (útil para el cliente
y para el diagnóstico), mientras `code` es el contrato estable. Los handlers se
registran desde `create_app` mediante `registrar_manejadores_de_errores`.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.domain.exceptions import (
    SolapamientoProfesionalError,
    SolapamientoSillonError,
    TransicionInvalidaError,
)


class ErrorTenantNoResuelto(Exception):
    """La petición no permite resolver un tenant válido (capa API, design D4)."""

    def __init__(
        self, mensaje: str = "No se pudo resolver el tenant de la petición"
    ) -> None:
        super().__init__(mensaje)


class ErrorCredencialesInvalidas(Exception):
    """Las credenciales de acceso son incorrectas o el usuario está inactivo."""

    def __init__(self, mensaje: str = "Credenciales inválidas") -> None:
        super().__init__(mensaje)


class ErrorNoAutenticado(Exception):
    """Falta cabecera de autorización o credenciales Bearer."""

    def __init__(self, mensaje: str = "No autenticado") -> None:
        super().__init__(mensaje)


class ErrorTokenExpirado(Exception):
    """El token JWT ha expirado."""

    def __init__(self, mensaje: str = "Token expirado") -> None:
        super().__init__(mensaje)


class ErrorTokenInvalido(Exception):
    """El token JWT es inválido o su firma no coincide."""

    def __init__(self, mensaje: str = "Token inválido") -> None:
        super().__init__(mensaje)


class ErrorAccesoDenegado(Exception):
    """El usuario autenticado no posee el rol necesario para la operación."""

    def __init__(self, mensaje: str = "Acceso denegado") -> None:
        super().__init__(mensaje)


class ErrorTurnoNoEncontrado(Exception):
    """El turno solicitado no existe en el tenant resuelto."""

    def __init__(self, mensaje: str = "Turno no encontrado") -> None:
        super().__init__(mensaje)


class ErrorPacienteDuplicado(Exception):
    """Ya existe un paciente con el mismo DNI en el tenant (C-07)."""

    def __init__(
        self,
        mensaje: str = "Ya existe un paciente con el DNI indicado en este centro",
    ) -> None:
        super().__init__(mensaje)


def respuesta_error(status_code: int, code: str, message: str) -> JSONResponse:
    """Construye la respuesta JSON con el envelope de error único."""
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def _manejar_solapamiento_profesional(
    _request: Request, exc: SolapamientoProfesionalError
) -> JSONResponse:
    return respuesta_error(409, "SOLAPAMIENTO_PROFESIONAL", str(exc))


def _manejar_solapamiento_sillon(
    _request: Request, exc: SolapamientoSillonError
) -> JSONResponse:
    return respuesta_error(409, "SOLAPAMIENTO_SILLON", str(exc))


def _manejar_transicion_invalida(
    _request: Request, exc: TransicionInvalidaError
) -> JSONResponse:
    return respuesta_error(409, "TRANSICION_INVALIDA", str(exc))


def _manejar_validacion(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    """422 con detalle legible por campo, sin trazas ni rutas internas."""
    detalles: list[str] = []
    for error in exc.errors():
        ubicacion = ".".join(str(parte) for parte in error.get("loc", ()))
        mensaje = error.get("msg", "valor inválido")
        detalles.append(f"{ubicacion}: {mensaje}" if ubicacion else str(mensaje))
    mensaje_estable = "; ".join(detalles) if detalles else "La petición no es válida"
    return respuesta_error(422, "VALIDACION", mensaje_estable)


def _manejar_tenant_no_resuelto(
    _request: Request, exc: ErrorTenantNoResuelto
) -> JSONResponse:
    return respuesta_error(400, "TENANT_NO_RESUELTO", str(exc))


def _manejar_credenciales_invalidas(
    _request: Request, exc: ErrorCredencialesInvalidas
) -> JSONResponse:
    return respuesta_error(401, "CREDENCIALES_INVALIDAS", str(exc))


def _manejar_no_autenticado(
    _request: Request, exc: ErrorNoAutenticado
) -> JSONResponse:
    return respuesta_error(401, "NO_AUTENTICADO", str(exc))


def _manejar_token_expirado(
    _request: Request, exc: ErrorTokenExpirado
) -> JSONResponse:
    return respuesta_error(401, "TOKEN_EXPIRADO", str(exc))


def _manejar_token_invalido(
    _request: Request, exc: ErrorTokenInvalido
) -> JSONResponse:
    return respuesta_error(401, "TOKEN_INVALIDO", str(exc))


def _manejar_acceso_denegado(
    _request: Request, exc: ErrorAccesoDenegado
) -> JSONResponse:
    return respuesta_error(403, "ACCESO_DENEGADO", str(exc))


def _manejar_turno_no_encontrado(
    _request: Request, exc: ErrorTurnoNoEncontrado
) -> JSONResponse:
    return respuesta_error(404, "TURNO_NO_ENCONTRADO", str(exc))


def _manejar_paciente_duplicado(
    _request: Request, exc: ErrorPacienteDuplicado
) -> JSONResponse:
    return respuesta_error(409, "PACIENTE_DUPLICADO", str(exc))


def registrar_manejadores_de_errores(app: FastAPI) -> None:
    """Registra en `app` los handlers del envelope (reutilizable por la factoría)."""
    app.add_exception_handler(
        SolapamientoProfesionalError, _manejar_solapamiento_profesional
    )
    app.add_exception_handler(SolapamientoSillonError, _manejar_solapamiento_sillon)
    app.add_exception_handler(TransicionInvalidaError, _manejar_transicion_invalida)
    app.add_exception_handler(RequestValidationError, _manejar_validacion)
    app.add_exception_handler(ErrorTenantNoResuelto, _manejar_tenant_no_resuelto)
    app.add_exception_handler(ErrorCredencialesInvalidas, _manejar_credenciales_invalidas)
    app.add_exception_handler(ErrorNoAutenticado, _manejar_no_autenticado)
    app.add_exception_handler(ErrorTokenExpirado, _manejar_token_expirado)
    app.add_exception_handler(ErrorTokenInvalido, _manejar_token_invalido)
    app.add_exception_handler(ErrorAccesoDenegado, _manejar_acceso_denegado)
    app.add_exception_handler(ErrorTurnoNoEncontrado, _manejar_turno_no_encontrado)
    app.add_exception_handler(ErrorPacienteDuplicado, _manejar_paciente_duplicado)
