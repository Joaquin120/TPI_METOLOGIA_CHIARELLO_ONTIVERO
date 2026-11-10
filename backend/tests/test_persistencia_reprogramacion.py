"""Pruebas de persistencia para reprogramación de turnos sobre SQLite real (C-08b, task 2.2)."""

from pathlib import Path
import pytest

from src.domain.models import Profesional, Sillon, Turno
from src.infrastructure.database import abrir_conexion, migrar
from src.infrastructure.seed import sembrar_datos_iniciales
from src.repositories.turnos_sqlite import RepositorioTurnosSqlite


@pytest.fixture
def repo_con_db(tmp_path: Path) -> tuple[RepositorioTurnosSqlite, Path, int]:
    ruta = tmp_path / "test_persistencia_reprogramar.db"
    conexion = abrir_conexion(ruta)
    migrar(conexion)
    sembrar_datos_iniciales(conexion)
    tenant_id = conexion.execute("SELECT id FROM tenant LIMIT 1").fetchone()[0]
    conexion.close()

    conn = abrir_conexion(ruta)
    repo = RepositorioTurnosSqlite(conn, tenant_id=tenant_id)
    return repo, ruta, tenant_id


def test_persistencia_reprogramacion_in_place(repo_con_db) -> None:
    repo, ruta, tenant_id = repo_con_db

    p = Profesional(nombre="Dr. Pérez")
    s = Sillon(nombre="Sillón 1")
    creado = repo.guardar(
        Turno(
            profesional=p,
            sillon=s,
            fecha="2026-11-01",
            hora_inicio="10:00",
            hora_fin="11:00",
            paciente="Paciente Persistencia",
        )
    )
    assert creado.id is not None

    reprogramado = repo.actualizar_reprogramacion(
        Turno(
            id=creado.id,
            profesional=p,
            sillon=s,
            fecha="2026-11-02",
            hora_inicio="15:00",
            hora_fin="16:00",
            paciente="Paciente Persistencia",
        )
    )

    # Verificar directamente en la base con otra conexión
    conn2 = abrir_conexion(ruta)
    try:
        fila = conn2.execute(
            "SELECT fecha_hora_inicio, fecha_hora_fin FROM turno WHERE id = ? AND tenant_id = ?",
            (creado.id, tenant_id),
        ).fetchone()
        assert fila is not None
        assert fila["fecha_hora_inicio"] == "2026-11-02 15:00"
        assert fila["fecha_hora_fin"] == "2026-11-02 16:00"
    finally:
        conn2.close()


def test_persistencia_reprogramacion_libera_horario_en_sql(repo_con_db) -> None:
    repo, ruta, tenant_id = repo_con_db

    p = Profesional(nombre="Dr. Pérez")
    s = Sillon(nombre="Sillón 1")
    creado = repo.guardar(
        Turno(
            profesional=p,
            sillon=s,
            fecha="2026-11-01",
            hora_inicio="10:00",
            hora_fin="11:00",
            paciente="Paciente 1",
        )
    )

    # Verificamos que solapa con 10:30-11:30
    solapados = repo.buscar_activos_solapables(
        fecha="2026-11-01",
        hora_inicio="10:30",
        hora_fin="11:30",
        profesional=p,
        sillon=s,
    )
    assert len(solapados) == 1

    # Reprogramamos a otro día
    repo.actualizar_reprogramacion(
        Turno(
            id=creado.id,
            profesional=p,
            sillon=s,
            fecha="2026-11-05",
            hora_inicio="10:00",
            hora_fin="11:00",
            paciente="Paciente 1",
        )
    )

    # Ahora el horario anterior debe estar completamente libre
    liberados = repo.buscar_activos_solapables(
        fecha="2026-11-01",
        hora_inicio="10:30",
        hora_fin="11:30",
        profesional=p,
        sillon=s,
    )
    assert len(liberados) == 0


def test_persistencia_buscar_activos_con_excluir_turno_id(repo_con_db) -> None:
    repo, _, _ = repo_con_db
    p = Profesional(nombre="Dr. Pérez")
    s = Sillon(nombre="Sillón 1")
    t1 = repo.guardar(
        Turno(
            profesional=p,
            sillon=s,
            fecha="2026-11-01",
            hora_inicio="10:00",
            hora_fin="11:00",
            paciente="Paciente 1",
        )
    )

    # Sin excluir: solapa
    candidatos_con = repo.buscar_activos_solapables(
        fecha="2026-11-01",
        hora_inicio="10:30",
        hora_fin="11:30",
        profesional=p,
        sillon=s,
    )
    assert len(candidatos_con) == 1
    assert candidatos_con[0].id == t1.id

    # Excluyendo el id del turno t1: resultado vacío (sin colisión)
    candidatos_sin = repo.buscar_activos_solapables(
        fecha="2026-11-01",
        hora_inicio="10:30",
        hora_fin="11:30",
        profesional=p,
        sillon=s,
        excluir_turno_id=t1.id,
    )
    assert len(candidatos_sin) == 0


def test_persistencia_reprogramacion_aislamiento_multitenant(tmp_path: Path) -> None:
    ruta = tmp_path / "test_aislamiento.db"
    conn = abrir_conexion(ruta)
    migrar(conn)
    sembrar_datos_iniciales(conn)

    # Crear tenant 2
    conn.execute("INSERT INTO tenant (nombre) VALUES ('Clínica Dos')")
    t2_id = conn.execute("SELECT id FROM tenant WHERE nombre = 'Clínica Dos'").fetchone()[0]
    conn.commit()

    t1_id = conn.execute("SELECT id FROM tenant WHERE nombre != 'Clínica Dos' LIMIT 1").fetchone()[0]

    repo_t1 = RepositorioTurnosSqlite(conn, tenant_id=t1_id)
    repo_t2 = RepositorioTurnosSqlite(conn, tenant_id=t2_id)

    # Crear turno en Tenant 1
    turno_t1 = repo_t1.guardar(
        Turno(
            profesional=Profesional(nombre="Dr. Uno"),
            sillon=Sillon(nombre="Sillón Uno"),
            fecha="2026-11-01",
            hora_inicio="10:00",
            hora_fin="10:30",
            paciente="Paciente T1",
        )
    )

    # Intentar obtener o actualizar desde Repo T2
    assert repo_t2.obtener_por_id(turno_t1.id) is None  # type: ignore[arg-type]

    # Actualizar desde Tenant 2 no afecta al registro de Tenant 1
    repo_t2.actualizar_reprogramacion(
        Turno(
            id=turno_t1.id,
            profesional=Profesional(nombre="Dr. Dos"),
            sillon=Sillon(nombre="Sillón Dos"),
            fecha="2026-11-02",
            hora_inicio="18:00",
            hora_fin="19:00",
            paciente="Paciente Hack",
        )
    )

    turno_intacto = repo_t1.obtener_por_id(turno_t1.id)  # type: ignore[arg-type]
    assert turno_intacto is not None
    assert turno_intacto.fecha == "2026-11-01"
    assert turno_intacto.hora_inicio == "10:00"
    conn.close()
