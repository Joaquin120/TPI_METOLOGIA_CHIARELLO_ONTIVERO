"""Pruebas del envelope de error y sus handlers (tasks 4.1 y 4.2, design D6).

Se usa una app FastAPI mínima de test (sin base de datos) que monta rutas que
lanzan las excepciones; el contrato verificado es
`{"error": {"code": ..., "message": ...}}`.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.errores import ErrorTenantNoResuelto, registrar_manejadores_de_errores
from src.api.esquemas import TurnoCrear
from src.domain.exceptions import (
    SolapamientoProfesionalError,
    SolapamientoSillonError,
    TransicionInvalidaError,
)


def _app_de_prueba() -> FastAPI:
    """App mínima con una ruta por excepción de dominio (sin persistencia)."""
    app = FastAPI()
    registrar_manejadores_de_errores(app)

    @app.get("/prueba/solapamiento-profesional")
    def _solapamiento_profesional() -> dict[str, str]:
        raise SolapamientoProfesionalError(
            "El profesional Dr. Ejemplo ya tiene un turno el 2026-11-01 de 10:00 a 10:30"
        )

    @app.get("/prueba/solapamiento-sillon")
    def _solapamiento_sillon() -> dict[str, str]:
        raise SolapamientoSillonError(
            "El sillón Sillón 1 ya está ocupado el 2026-11-01 de 10:00 a 10:30"
        )

    @app.get("/prueba/transicion-invalida")
    def _transicion_invalida() -> dict[str, str]:
        raise TransicionInvalidaError(
            "No se puede aplicar 'completar' sobre un turno en estado 'CANCELADO'"
        )

    @app.post("/prueba/validacion")
    def _validacion(turno: TurnoCrear) -> dict[str, str]:
        return {"paciente": turno.paciente}

    @app.get("/prueba/tenant-ausente")
    def _tenant_ausente() -> dict[str, str]:
        raise ErrorTenantNoResuelto("No se pudo resolver el tenant de la petición")

    @app.get("/prueba/tenant-inexistente")
    def _tenant_inexistente() -> dict[str, str]:
        raise ErrorTenantNoResuelto("El tenant 999 no existe")

    @app.get("/prueba/turno-no-encontrado")
    def _turno_no_encontrado() -> dict[str, str]:
        from src.api.errores import ErrorTurnoNoEncontrado

        raise ErrorTurnoNoEncontrado("Turno no encontrado")

    return app


@pytest.fixture()
def cliente() -> TestClient:
    return TestClient(_app_de_prueba())


# ---------------------------------------------------------------------------
# Task 4.1 — conflicto de dominio → 409 con envelope estable
# ---------------------------------------------------------------------------


def test_solapamiento_profesional_devuelve_409(cliente: TestClient) -> None:
    respuesta = cliente.get("/prueba/solapamiento-profesional")

    assert respuesta.status_code == 409
    assert respuesta.json() == {
        "error": {
            "code": "SOLAPAMIENTO_PROFESIONAL",
            "message": (
                "El profesional Dr. Ejemplo ya tiene un turno "
                "el 2026-11-01 de 10:00 a 10:30"
            ),
        }
    }


def test_solapamiento_sillon_devuelve_409(cliente: TestClient) -> None:
    respuesta = cliente.get("/prueba/solapamiento-sillon")

    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["code"] == "SOLAPAMIENTO_SILLON"
    assert respuesta.json()["error"]["message"] == (
        "El sillón Sillón 1 ya está ocupado el 2026-11-01 de 10:00 a 10:30"
    )


def test_transicion_invalida_devuelve_409(cliente: TestClient) -> None:
    respuesta = cliente.get("/prueba/transicion-invalida")

    assert respuesta.status_code == 409
    assert respuesta.json() == {
        "error": {
            "code": "TRANSICION_INVALIDA",
            "message": (
                "No se puede aplicar 'completar' sobre un turno en estado 'CANCELADO'"
            ),
        }
    }


def test_envelope_conserva_el_mensaje_por_defecto_del_dominio() -> None:
    """Triangulación: sin mensaje explícito se conserva el texto de la excepción."""
    app = FastAPI()
    registrar_manejadores_de_errores(app)

    @app.get("/prueba/sillon-sin-mensaje")
    def _sillon_sin_mensaje() -> dict[str, str]:
        raise SolapamientoSillonError()

    respuesta = TestClient(app).get("/prueba/sillon-sin-mensaje")

    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["message"] == (
        "El sillón ya está ocupado en ese horario"
    )


# ---------------------------------------------------------------------------
# Task 4.2 — validación → 422 y tenant → 400
# ---------------------------------------------------------------------------


def _payload_valido() -> dict[str, str]:
    return {
        "paciente": "Paciente Ficticio",
        "profesional": "Dr. Ejemplo",
        "sillon": "Sillón 1",
        "fecha": "2026-11-01",
        "hora_inicio": "10:00",
        "hora_fin": "10:30",
    }


def test_campo_faltante_devuelve_422_validacion(cliente: TestClient) -> None:
    payload = _payload_valido()
    del payload["hora_fin"]

    respuesta = cliente.post("/prueba/validacion", json=payload)

    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "VALIDACION"
    assert isinstance(respuesta.json()["error"]["message"], str)
    assert respuesta.json()["error"]["message"]


def test_hora_invalida_devuelve_422_validacion(cliente: TestClient) -> None:
    respuesta = cliente.post(
        "/prueba/validacion", json={**_payload_valido(), "hora_inicio": "25:99"}
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "VALIDACION"


def test_validacion_no_filtra_trazas_internas(cliente: TestClient) -> None:
    """REFACTOR 4.2: el mensaje es estable y no expone trazas ni rutas internas."""
    payload = _payload_valido()
    del payload["fecha"]

    respuesta = cliente.post("/prueba/validacion", json=payload)
    mensaje = respuesta.json()["error"]["message"]

    assert respuesta.status_code == 422
    assert "Traceback" not in mensaje
    assert ".py" not in mensaje
    assert "fecha" in mensaje


def test_tenant_ausente_devuelve_400(cliente: TestClient) -> None:
    respuesta = cliente.get("/prueba/tenant-ausente")

    assert respuesta.status_code == 400
    assert respuesta.json() == {
        "error": {
            "code": "TENANT_NO_RESUELTO",
            "message": "No se pudo resolver el tenant de la petición",
        }
    }


def test_tenant_inexistente_devuelve_400(cliente: TestClient) -> None:
    respuesta = cliente.get("/prueba/tenant-inexistente")

    assert respuesta.status_code == 400
    assert respuesta.json()["error"]["code"] == "TENANT_NO_RESUELTO"
    assert respuesta.json()["error"]["message"] == "El tenant 999 no existe"


def test_turno_no_encontrado_devuelve_404(cliente: TestClient) -> None:
    """Task 2.1: ErrorTurnoNoEncontrado se mapea a 404 con envelope estándar."""
    respuesta = cliente.get("/prueba/turno-no-encontrado")

    assert respuesta.status_code == 404
    assert respuesta.json() == {
        "error": {
            "code": "TURNO_NO_ENCONTRADO",
            "message": "Turno no encontrado",
        }
    }

