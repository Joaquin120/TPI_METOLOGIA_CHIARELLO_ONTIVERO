"""Pruebas de integración del slice vertical de turnos (tasks 7.1–7.4).

`TestClient` + SQLite real en archivo temporal (`tmp_path`), migrado y sembrado.
Nunca se mockea la base (regla dura 5). Solo datos sintéticos (regla dura 3).
La doble validación y las transiciones se delegan al dominio: la API no las
reimplementa (regla dura 2).
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.infrastructure.database import abrir_conexion
from src.infrastructure.seed import TENANT_DEFECTO


def _payload(**cambios: object) -> dict[str, object]:
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


def _id_tenant(ruta: Path, nombre: str = TENANT_DEFECTO) -> int:
    conexion = abrir_conexion(ruta)
    try:
        return conexion.execute(
            "SELECT id FROM tenant WHERE nombre = ?", (nombre,)
        ).fetchone()[0]
    finally:
        conexion.close()


def _crear_tenant_extra(ruta: Path, nombre: str = "Clínica Secundaria") -> int:
    conexion: sqlite3.Connection = abrir_conexion(ruta)
    try:
        conexion.execute("INSERT INTO tenant (nombre) VALUES (?)", (nombre,))
        conexion.commit()
    finally:
        conexion.close()
    return _id_tenant(ruta, nombre)


def _crear_cliente(ruta: Path) -> tuple[TestClient, int]:
    app = create_app(ruta_db=ruta, sembrar=True)
    return TestClient(app), _id_tenant(ruta)


def _headers(tenant_id: int) -> dict[str, str]:
    return {"X-Tenant-ID": str(tenant_id)}


def _contar_turnos(ruta: Path, tenant_id: int) -> int:
    conexion: sqlite3.Connection = abrir_conexion(ruta)
    try:
        return conexion.execute(
            "SELECT COUNT(*) FROM turno WHERE tenant_id = ?", (tenant_id,)
        ).fetchone()[0]
    finally:
        conexion.close()


@pytest.fixture()
def api(tmp_path: Path) -> tuple[TestClient, int, Path]:
    ruta = tmp_path / "api_turnos.db"
    cliente, tenant_id = _crear_cliente(ruta)
    return cliente, tenant_id, ruta


# ---------------------------------------------------------------------------
# Task 7.1 — POST /api/v1/turnos
# ---------------------------------------------------------------------------


def test_post_alta_exitosa_devuelve_201_con_datos_ecoados(api) -> None:
    cliente, tenant_id, _ruta = api

    respuesta = cliente.post("/api/v1/turnos", json=_payload(), headers=_headers(tenant_id))

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert isinstance(cuerpo["id"], int)
    assert cuerpo == {
        "id": cuerpo["id"],
        "paciente": "Paciente Ficticio",
        "profesional": "Dr. Ejemplo",
        "sillon": "Sillón 1",
        "fecha": "2026-11-01",
        "hora_inicio": "10:00",
        "hora_fin": "10:30",
        "estado": "CONFIRMADO",
    }


def test_post_segundo_alta_en_otro_horario_y_sillon(api) -> None:
    """Triangulación: un segundo alta válida con otros datos devuelve otro id."""
    cliente, tenant_id, _ruta = api
    primero = cliente.post("/api/v1/turnos", json=_payload(), headers=_headers(tenant_id))
    segundo = cliente.post(
        "/api/v1/turnos",
        json=_payload(
            paciente="Paciente Ficticio 2",
            profesional="Dra. Ejemplo",
            sillon="Sillón 2",
            hora_inicio="11:00",
            hora_fin="11:30",
        ),
        headers=_headers(tenant_id),
    )

    assert primero.status_code == 201
    assert segundo.status_code == 201
    assert primero.json()["id"] != segundo.json()["id"]
    assert segundo.json()["sillon"] == "Sillón 2"


def test_post_contiguo_en_el_limite_es_permitido(api) -> None:
    """Triangulación borde: `[inicio, fin)` permite un alta que empieza en 10:30."""
    cliente, tenant_id, _ruta = api
    primero = cliente.post("/api/v1/turnos", json=_payload(), headers=_headers(tenant_id))
    contiguo = cliente.post(
        "/api/v1/turnos",
        json=_payload(
            hora_inicio="10:30",
            hora_fin="11:00",
            paciente="Paciente Ficticio 2",
        ),
        headers=_headers(tenant_id),
    )

    assert primero.status_code == 201
    assert contiguo.status_code == 201


def test_turno_creado_por_la_api_queda_persistido(api) -> None:
    cliente, tenant_id, ruta = api

    respuesta = cliente.post("/api/v1/turnos", json=_payload(), headers=_headers(tenant_id))

    assert respuesta.status_code == 201
    assert _contar_turnos(ruta, tenant_id) == 1
    conexion = abrir_conexion(ruta)
    try:
        fila = conexion.execute(
            "SELECT estado, fecha_hora_inicio, fecha_hora_fin FROM turno WHERE tenant_id = ?",
            (tenant_id,),
        ).fetchone()
    finally:
        conexion.close()
    assert tuple(fila) == ("CONFIRMADO", "2026-11-01 10:00", "2026-11-01 10:30")


# ---------------------------------------------------------------------------
# Task 7.2 — GET /api/v1/turnos
# ---------------------------------------------------------------------------


def test_get_listado_devuelve_los_dos_turnos_del_tenant_ordenados(api) -> None:
    cliente, tenant_id, _ruta = api
    cliente.post("/api/v1/turnos", json=_payload(), headers=_headers(tenant_id))
    cliente.post(
        "/api/v1/turnos",
        json=_payload(
            paciente="Paciente Ficticio 2",
            profesional="Dra. Ejemplo",
            sillon="Sillón 2",
            hora_inicio="11:00",
            hora_fin="11:30",
        ),
        headers=_headers(tenant_id),
    )

    respuesta = cliente.get("/api/v1/turnos", headers=_headers(tenant_id))

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert len(cuerpo) == 2
    assert [turno["hora_inicio"] for turno in cuerpo] == ["10:00", "11:00"]
    assert [turno["paciente"] for turno in cuerpo] == [
        "Paciente Ficticio",
        "Paciente Ficticio 2",
    ]
    assert cuerpo[0]["profesional"] == "Dr. Ejemplo"
    assert cuerpo[1]["sillon"] == "Sillón 2"
    assert all(turno["estado"] == "CONFIRMADO" for turno in cuerpo)


def test_get_turno_creado_aparece_en_el_listado(api) -> None:
    """Escenario 'El turno creado por la API queda persistido' (vía GET)."""
    cliente, tenant_id, _ruta = api
    creado = cliente.post(
        "/api/v1/turnos", json=_payload(), headers=_headers(tenant_id)
    ).json()

    listado = cliente.get("/api/v1/turnos", headers=_headers(tenant_id)).json()

    assert listado == [creado]


def test_get_tenant_sin_turnos_devuelve_lista_vacia(api) -> None:
    """Triangulación: un tenant válido sin turnos responde `[]`."""
    cliente, tenant_id, _ruta = api

    respuesta = cliente.get("/api/v1/turnos", headers=_headers(tenant_id))

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_get_no_incluye_turnos_de_otro_tenant(api) -> None:
    """Aislamiento: el tenant B no ve el turno persistido en el tenant A."""
    cliente, tenant_a, ruta = api
    tenant_b = _crear_tenant_extra(ruta)
    cliente.post("/api/v1/turnos", json=_payload(), headers=_headers(tenant_a))

    respuesta = cliente.get("/api/v1/turnos", headers=_headers(tenant_b))

    assert respuesta.status_code == 200
    assert respuesta.json() == []
    assert _contar_turnos(ruta, tenant_a) == 1
    assert _contar_turnos(ruta, tenant_b) == 0


# ---------------------------------------------------------------------------
# Task 7.3 — conflictos de la doble validación mapeados a 409
# ---------------------------------------------------------------------------


def test_conflicto_de_profesional_devuelve_409_y_no_persiste(api) -> None:
    """El profesional cambia de sillón pero sigue ocupado: 409 del dominio."""
    cliente, tenant_id, ruta = api
    cliente.post("/api/v1/turnos", json=_payload(), headers=_headers(tenant_id))

    respuesta = cliente.post(
        "/api/v1/turnos",
        json=_payload(
            paciente="Paciente Ficticio 2",
            sillon="Sillón 2",
            hora_inicio="10:15",
            hora_fin="10:45",
        ),
        headers=_headers(tenant_id),
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["code"] == "SOLAPAMIENTO_PROFESIONAL"
    assert "Dr. Ejemplo" in respuesta.json()["error"]["message"]
    assert _contar_turnos(ruta, tenant_id) == 1
    assert len(cliente.get("/api/v1/turnos", headers=_headers(tenant_id)).json()) == 1


def test_conflicto_de_sillon_devuelve_409_y_no_persiste(api) -> None:
    """Triangulación: el sillón ocupado por otro profesional también es 409."""
    cliente, tenant_id, ruta = api
    cliente.post("/api/v1/turnos", json=_payload(), headers=_headers(tenant_id))

    respuesta = cliente.post(
        "/api/v1/turnos",
        json=_payload(
            paciente="Paciente Ficticio 2",
            profesional="Dra. Ejemplo",
            hora_inicio="10:15",
            hora_fin="10:45",
        ),
        headers=_headers(tenant_id),
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["code"] == "SOLAPAMIENTO_SILLON"
    assert "Sillón 1" in respuesta.json()["error"]["message"]
    assert _contar_turnos(ruta, tenant_id) == 1


# ---------------------------------------------------------------------------
# Task 7.4 — validación del router real mapeada a 422
# ---------------------------------------------------------------------------


def test_post_sin_hora_fin_devuelve_422_y_no_crea_turno(api) -> None:
    cliente, tenant_id, ruta = api
    payload = _payload()
    del payload["hora_fin"]

    respuesta = cliente.post("/api/v1/turnos", json=payload, headers=_headers(tenant_id))

    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "VALIDACION"
    assert _contar_turnos(ruta, tenant_id) == 0
    assert cliente.get("/api/v1/turnos", headers=_headers(tenant_id)).json() == []


def test_post_con_hora_invalida_devuelve_422_y_no_crea_turno(api) -> None:
    cliente, tenant_id, ruta = api

    respuesta = cliente.post(
        "/api/v1/turnos",
        json=_payload(hora_inicio="25:99"),
        headers=_headers(tenant_id),
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "VALIDACION"
    assert _contar_turnos(ruta, tenant_id) == 0


def test_post_valido_de_control_sigue_creando_turno(api) -> None:
    """Triangulación de control: el mismo router acepta el payload válido."""
    cliente, tenant_id, ruta = api

    respuesta = cliente.post("/api/v1/turnos", json=_payload(), headers=_headers(tenant_id))

    assert respuesta.status_code == 201
    assert _contar_turnos(ruta, tenant_id) == 1
