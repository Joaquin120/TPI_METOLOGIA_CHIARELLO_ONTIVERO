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
from src.api.seguridad import crear_token_acceso
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


def _headers(tenant_id: int, rol: str = "Recepcionista") -> dict[str, str]:
    token = crear_token_acceso({
        "sub": "1",
        "email": f"recepcion@{tenant_id}.com",
        "tenant_id": tenant_id,
        "rol": rol,
    })
    return {"Authorization": f"Bearer {token}"}


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


# ---------------------------------------------------------------------------
# C-04 — Autenticación y RBAC en endpoints de turnos
# ---------------------------------------------------------------------------


def test_post_sin_autenticacion_devuelve_401(api) -> None:
    cliente, _tenant_id, ruta = api
    resp = cliente.post("/api/v1/turnos", json=_payload())
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "NO_AUTENTICADO"
    assert _contar_turnos(ruta, 1) == 0


def test_get_sin_autenticacion_devuelve_401(api) -> None:
    cliente, _tenant_id, _ruta = api
    resp = cliente.get("/api/v1/turnos")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "NO_AUTENTICADO"


def test_post_rol_profesional_devuelve_403(api) -> None:
    cliente, tenant_id, ruta = api
    headers_prof = _headers(tenant_id, rol="Profesional")
    resp = cliente.post("/api/v1/turnos", json=_payload(), headers=headers_prof)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "ACCESO_DENEGADO"
    assert _contar_turnos(ruta, tenant_id) == 0


# ---------------------------------------------------------------------------
# C-05: Task 3.1 - Filtros opcionales en GET /api/v1/turnos
# ---------------------------------------------------------------------------


def test_get_turnos_filtrado_por_fecha(api) -> None:
    """Task 3.1: GET /api/v1/turnos?fecha=YYYY-MM-DD filtra por fecha."""
    cliente, tenant_id, _ruta = api
    t1 = cliente.post("/api/v1/turnos", json=_payload(fecha="2026-11-01"), headers=_headers(tenant_id)).json()
    _t2 = cliente.post("/api/v1/turnos", json=_payload(fecha="2026-11-02"), headers=_headers(tenant_id)).json()

    resp = cliente.get("/api/v1/turnos?fecha=2026-11-01", headers=_headers(tenant_id))
    assert resp.status_code == 200
    turnos = resp.json()
    assert len(turnos) == 1
    assert turnos[0]["id"] == t1["id"]
    assert turnos[0]["fecha"] == "2026-11-01"


def test_get_turnos_filtrado_por_profesional_id(api) -> None:
    """Task 3.1: GET /api/v1/turnos?profesional_id=... filtra por profesional."""
    cliente, tenant_id, _ruta = api
    t1 = cliente.post("/api/v1/turnos", json=_payload(profesional="Dr. Ejemplo"), headers=_headers(tenant_id)).json()
    _t2 = cliente.post("/api/v1/turnos", json=_payload(profesional="Dra. Ejemplo", sillon="Sillón 2"), headers=_headers(tenant_id)).json()

    # profesional 1 es Dr. Ejemplo
    resp = cliente.get("/api/v1/turnos?profesional_id=1", headers=_headers(tenant_id))
    assert resp.status_code == 200
    turnos = resp.json()
    assert len(turnos) == 1
    assert turnos[0]["id"] == t1["id"]
    assert turnos[0]["profesional"] == "Dr. Ejemplo"


def test_get_turnos_filtrado_por_sillon_id(api) -> None:
    """Task 3.1: GET /api/v1/turnos?sillon_id=... filtra por sillón."""
    cliente, tenant_id, _ruta = api
    _t1 = cliente.post("/api/v1/turnos", json=_payload(sillon="Sillón 1"), headers=_headers(tenant_id)).json()
    t2 = cliente.post("/api/v1/turnos", json=_payload(profesional="Dra. Ejemplo", sillon="Sillón 2"), headers=_headers(tenant_id)).json()

    # sillon 2 es Sillón 2
    resp = cliente.get("/api/v1/turnos?sillon_id=2", headers=_headers(tenant_id))
    assert resp.status_code == 200
    turnos = resp.json()
    assert len(turnos) == 1
    assert turnos[0]["id"] == t2["id"]
    assert turnos[0]["sillon"] == "Sillón 2"


def test_get_turnos_filtrado_combinado_sin_coincidencias(api) -> None:
    """Task 3.1: combinación de filtros con conjunción lógica (AND)."""
    cliente, tenant_id, _ruta = api
    cliente.post("/api/v1/turnos", json=_payload(fecha="2026-11-01", sillon="Sillón 1"), headers=_headers(tenant_id))

    resp = cliente.get("/api/v1/turnos?fecha=2026-11-02&sillon_id=1", headers=_headers(tenant_id))
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_turnos_fecha_invalida_devuelve_422(api) -> None:
    """Task 3.1: formato de fecha inválido devuelve 422 VALIDACION."""
    cliente, tenant_id, _ruta = api

    resp = cliente.get("/api/v1/turnos?fecha=01-11-2026", headers=_headers(tenant_id))
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDACION"


# ---------------------------------------------------------------------------
# C-05: Task 4.1 - PATCH /api/v1/turnos/{id}/estado
# ---------------------------------------------------------------------------


def test_patch_estado_cancelar_exitoso(api) -> None:
    """Task 4.1: Recepcionista puede cancelar un turno confirmado y pasa a CANCELADO."""
    cliente, tenant_id, _ruta = api
    creado = cliente.post("/api/v1/turnos", json=_payload(), headers=_headers(tenant_id)).json()
    turno_id = creado["id"]

    resp = cliente.patch(
        f"/api/v1/turnos/{turno_id}/estado",
        json={"accion": "cancelar"},
        headers=_headers(tenant_id),
    )
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["id"] == turno_id
    assert cuerpo["estado"] == "CANCELADO"


def test_patch_estado_completar_exitoso(api) -> None:
    """Task 4.1: Recepcionista/Admin puede completar un turno confirmado y pasa a COMPLETADO."""
    cliente, tenant_id, _ruta = api
    creado = cliente.post("/api/v1/turnos", json=_payload(), headers=_headers(tenant_id)).json()
    turno_id = creado["id"]

    resp = cliente.patch(
        f"/api/v1/turnos/{turno_id}/estado",
        json={"accion": "completar"},
        headers=_headers(tenant_id),
    )
    assert resp.status_code == 200
    assert resp.json()["estado"] == "COMPLETADO"


def test_patch_estado_turno_inexistente_devuelve_404(api) -> None:
    """Task 4.1: id de turno inexistente en el tenant devuelve 404 TURNO_NO_ENCONTRADO."""
    cliente, tenant_id, _ruta = api

    resp = cliente.patch(
        "/api/v1/turnos/9999/estado",
        json={"accion": "cancelar"},
        headers=_headers(tenant_id),
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "TURNO_NO_ENCONTRADO"


def test_patch_estado_otro_tenant_devuelve_404(api) -> None:
    """Task 4.1: intentar cambiar estado de un turno perteneciente a otro tenant devuelve 404."""
    cliente, tenant_a, ruta = api
    tenant_b = _crear_tenant_extra(ruta)

    creado = cliente.post("/api/v1/turnos", json=_payload(), headers=_headers(tenant_a)).json()
    turno_id = creado["id"]

    resp = cliente.patch(
        f"/api/v1/turnos/{turno_id}/estado",
        json={"accion": "cancelar"},
        headers=_headers(tenant_b),
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "TURNO_NO_ENCONTRADO"


def test_patch_estado_transicion_invalida_devuelve_409(api) -> None:
    """Task 4.1: intentar transición inválida (cancelado -> completar) devuelve 409 TRANSICION_INVALIDA."""
    cliente, tenant_id, _ruta = api
    creado = cliente.post("/api/v1/turnos", json=_payload(), headers=_headers(tenant_id)).json()
    turno_id = creado["id"]

    # Cancelar turno
    cliente.patch(
        f"/api/v1/turnos/{turno_id}/estado",
        json={"accion": "cancelar"},
        headers=_headers(tenant_id),
    )

    # Intentar completar un turno cancelado
    resp = cliente.patch(
        f"/api/v1/turnos/{turno_id}/estado",
        json={"accion": "completar"},
        headers=_headers(tenant_id),
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "TRANSICION_INVALIDA"


def test_patch_estado_rol_profesional_devuelve_403(api) -> None:
    """Task 4.1: el rol Profesional no está autorizado para cambiar estados y recibe 403."""
    cliente, tenant_id, _ruta = api
    creado = cliente.post("/api/v1/turnos", json=_payload(), headers=_headers(tenant_id)).json()
    turno_id = creado["id"]

    headers_prof = _headers(tenant_id, rol="Profesional")
    resp = cliente.patch(
        f"/api/v1/turnos/{turno_id}/estado",
        json={"accion": "cancelar"},
        headers=headers_prof,
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "ACCESO_DENEGADO"


def test_patch_estado_accion_invalida_devuelve_422(api) -> None:
    """Task 4.1: acción desconocida devuelve 422 VALIDACION."""
    cliente, tenant_id, _ruta = api

    resp = cliente.patch(
        "/api/v1/turnos/1/estado",
        json={"accion": "accion_fantasma"},
        headers=_headers(tenant_id),
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDACION"


# ---------------------------------------------------------------------------
# C-05: Task 4.2 - Liberación inmediata de recursos (RN-04) vía HTTP
# ---------------------------------------------------------------------------


def test_cancelacion_via_patch_libera_recursos_para_nuevo_post(api) -> None:
    """Task 4.2: cancelar un turno vía PATCH libera al profesional y sillón de inmediato para nuevos agendamientos."""
    cliente, tenant_id, _ruta = api

    payload_turno = _payload(
        fecha="2026-11-20",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional="Dr. Ejemplo",
        sillon="Sillón 1",
    )

    # 1. Crear turno inicial
    resp1 = cliente.post("/api/v1/turnos", json=payload_turno, headers=_headers(tenant_id))
    assert resp1.status_code == 201
    turno1_id = resp1.json()["id"]

    # 2. Intentar agendar en conflicto -> 409
    resp_conflicto = cliente.post(
        "/api/v1/turnos",
        json=_payload(
            fecha="2026-11-20",
            hora_inicio="10:15",
            hora_fin="10:45",
            profesional="Dr. Ejemplo",
            sillon="Sillón 2",
        ),
        headers=_headers(tenant_id),
    )
    assert resp_conflicto.status_code == 409

    # 3. Cancelar turno inicial vía PATCH
    resp_cancelar = cliente.patch(
        f"/api/v1/turnos/{turno1_id}/estado",
        json={"accion": "cancelar"},
        headers=_headers(tenant_id),
    )
    assert resp_cancelar.status_code == 200
    assert resp_cancelar.json()["estado"] == "CANCELADO"

    # 4. Ahora el intervalo liberado permite el nuevo agendamiento (RN-04)
    resp2 = cliente.post(
        "/api/v1/turnos",
        json=_payload(
            fecha="2026-11-20",
            hora_inicio="10:15",
            hora_fin="10:45",
            profesional="Dr. Ejemplo",
            sillon="Sillón 2",
        ),
        headers=_headers(tenant_id),
    )
    assert resp2.status_code == 201
    assert resp2.json()["estado"] == "CONFIRMADO"



