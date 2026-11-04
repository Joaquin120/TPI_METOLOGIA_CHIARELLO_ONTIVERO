"""Pruebas de los esquemas Pydantic del contrato (tasks 3.1 y 3.2, design D5).

Contrato: campos no vacíos, `fecha` `YYYY-MM-DD`, horas `HH:MM` 24 h y
`extra="forbid"` (el cliente no puede inyectar `tenant_id`).
Regla dura 3: todos los datos son sintéticos.
"""

import pytest
from pydantic import ValidationError

from src.api.esquemas import TurnoCrear, TurnoRespuesta
from src.domain.models import CANCELADO, CONFIRMADO, Profesional, Sillon, Turno


def _payload_valido(**cambios: object) -> dict[str, object]:
    """Payload sintético base del escenario 'Alta exitosa' de la spec."""
    base: dict[str, object] = {
        "paciente": "Paciente Ficticio",
        "profesional": "Dr. Ejemplo",
        "sillon": "Sillón 1",
        "fecha": "2026-11-01",
        "hora_inicio": "10:00",
        "hora_fin": "10:30",
    }
    base.update(cambios)
    return base


# ---------------------------------------------------------------------------
# Task 3.1 — RED/GREEN de `TurnoCrear`
# ---------------------------------------------------------------------------


def test_turno_crear_acepta_payload_valido() -> None:
    """El payload canónico del contrato se acepta y conserva sus valores."""
    esquema = TurnoCrear(**_payload_valido())

    assert esquema.paciente == "Paciente Ficticio"
    assert esquema.profesional == "Dr. Ejemplo"
    assert esquema.sillon == "Sillón 1"
    assert esquema.fecha == "2026-11-01"
    assert esquema.hora_inicio == "10:00"
    assert esquema.hora_fin == "10:30"


def test_turno_crear_triangula_acentos_y_espacios_internos() -> None:
    """Triangulación: nombres con acentos y espacios internos son válidos."""
    esquema = TurnoCrear(
        **_payload_valido(
            paciente="Paciente Ficticio Número 2",
            profesional="Dra. Ejemplo",
            sillon="Sillón 2",
            hora_inicio="08:05",
            hora_fin="09:00",
        )
    )

    assert esquema.paciente == "Paciente Ficticio Número 2"
    assert esquema.profesional == "Dra. Ejemplo"
    assert esquema.sillon == "Sillón 2"
    assert esquema.hora_inicio == "08:05"


def test_turno_crear_rechaza_campo_faltante() -> None:
    """Falta `hora_fin`: ValidationError."""
    payload = _payload_valido()
    del payload["hora_fin"]

    with pytest.raises(ValidationError):
        TurnoCrear(**payload)


def test_turno_crear_rechaza_hora_con_formato_invalido() -> None:
    """`hora_inicio = "25:99"` no es una hora HH:MM de 24 h."""
    with pytest.raises(ValidationError):
        TurnoCrear(**_payload_valido(hora_inicio="25:99"))


def test_turno_crear_rechaza_fecha_invalida() -> None:
    """`fecha = "01-11-2026"` no cumple `YYYY-MM-DD`."""
    with pytest.raises(ValidationError):
        TurnoCrear(**_payload_valido(fecha="01-11-2026"))


def test_turno_crear_rechaza_campo_extra_tenant_id() -> None:
    """`extra="forbid"`: el cliente no puede inyectar `tenant_id` en el cuerpo."""
    with pytest.raises(ValidationError):
        TurnoCrear(**_payload_valido(tenant_id=1))


def test_turno_crear_rechaza_string_vacio() -> None:
    """Triangulación inválida: un nombre vacío no es un recurso válido."""
    with pytest.raises(ValidationError):
        TurnoCrear(**_payload_valido(paciente=""))


def test_turno_crear_rechaza_hora_de_un_digito() -> None:
    """Triangulación inválida adicional: `9:00` no es `HH:MM` estricto."""
    with pytest.raises(ValidationError):
        TurnoCrear(**_payload_valido(hora_inicio="9:00"))


# ---------------------------------------------------------------------------
# Task 3.2 — `TurnoRespuesta.desde_dominio`
# ---------------------------------------------------------------------------


def test_turno_respuesta_mapea_turno_confirmado() -> None:
    """Un turno CONFIRMADO con id expone los siete campos del contrato."""
    turno = Turno(
        profesional=Profesional(nombre="Dr. Ejemplo", id=3),
        sillon=Sillon(nombre="Sillón 1", id=5),
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        paciente="Paciente Ficticio",
        estado=CONFIRMADO,
        id=42,
    )

    respuesta = TurnoRespuesta.desde_dominio(turno)

    assert respuesta.model_dump() == {
        "id": 42,
        "paciente": "Paciente Ficticio",
        "profesional": "Dr. Ejemplo",
        "sillon": "Sillón 1",
        "fecha": "2026-11-01",
        "hora_inicio": "10:00",
        "hora_fin": "10:30",
        "estado": "CONFIRMADO",
    }


def test_turno_respuesta_triangula_turno_cancelado() -> None:
    """Triangulación: otro estado y otros datos no se pierden ni se renombran."""
    turno = Turno(
        profesional=Profesional(nombre="Dra. Ejemplo", id=4),
        sillon=Sillon(nombre="Sillón 2", id=6),
        fecha="2026-12-24",
        hora_inicio="08:15",
        hora_fin="09:45",
        paciente="Paciente Ficticio 2",
        estado=CANCELADO,
        id=7,
    )

    respuesta = TurnoRespuesta.desde_dominio(turno)

    assert respuesta.model_dump() == {
        "id": 7,
        "paciente": "Paciente Ficticio 2",
        "profesional": "Dra. Ejemplo",
        "sillon": "Sillón 2",
        "fecha": "2026-12-24",
        "hora_inicio": "08:15",
        "hora_fin": "09:45",
        "estado": "CANCELADO",
    }
    assert set(TurnoRespuesta.model_fields) == {
        "id",
        "paciente",
        "profesional",
        "sillon",
        "fecha",
        "hora_inicio",
        "hora_fin",
        "estado",
    }

