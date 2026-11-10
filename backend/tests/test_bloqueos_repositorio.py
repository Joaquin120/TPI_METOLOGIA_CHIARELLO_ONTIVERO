"""Pruebas de persistencia para RepositorioBloqueosSqlite sobre SQLite real (C-10, task 2.1 y 2.2)."""

from pathlib import Path
import pytest

from src.domain.models import BloqueoSillon
from src.infrastructure.database import abrir_conexion, migrar
from src.infrastructure.seed import TENANT_DEFECTO, sembrar_datos_iniciales
from src.repositories.bloqueos_sqlite import RepositorioBloqueosSqlite


@pytest.fixture
def repo_con_db(tmp_path: Path):
    ruta = tmp_path / "test_bloqueos_repo.db"
    conn = abrir_conexion(ruta)
    migrar(conn)
    sembrar_datos_iniciales(conn)
    tenant_id = conn.execute("SELECT id FROM tenant WHERE nombre = ?", (TENANT_DEFECTO,)).fetchone()[0]
    conn.execute("INSERT INTO tenant (nombre) VALUES ('Clínica Secundaria')")
    t2_id = conn.execute("SELECT id FROM tenant WHERE nombre = 'Clínica Secundaria'").fetchone()[0]
    conn.commit()
    conn.close()

    conn_activa = abrir_conexion(ruta)
    repo = RepositorioBloqueosSqlite(conn_activa, tenant_id=tenant_id)
    yield repo, conn_activa, tenant_id, t2_id, ruta
    conn_activa.close()


def test_guardar_y_obtener_por_id_bloqueo(repo_con_db):
    repo, _, tenant_id, _, _ = repo_con_db

    bloqueo = BloqueoSillon(
        tenant_id=tenant_id,
        sillon_id=1,
        fecha_hora_inicio="2026-11-20 08:00",
        fecha_hora_fin="2026-11-20 12:00",
        motivo="Mantenimiento preventivo anual",
    )
    guardado = repo.guardar(bloqueo)

    assert guardado.id is not None
    assert guardado.tenant_id == tenant_id
    assert guardado.creado_en is not None

    recuperado = repo.obtener_por_id(guardado.id)
    assert recuperado is not None
    assert recuperado.id == guardado.id
    assert recuperado.motivo == "Mantenimiento preventivo anual"


def test_buscar_bloqueos_solapados_formula_semiabierta(repo_con_db):
    repo, _, tenant_id, _, _ = repo_con_db

    repo.guardar(
        BloqueoSillon(
            tenant_id=tenant_id,
            sillon_id=1,
            fecha_hora_inicio="2026-11-20 08:00",
            fecha_hora_fin="2026-11-20 12:00",
            motivo="Mantenimiento",
        )
    )

    # 1. Solapa parcial anterior: 07:00 a 09:00 -> solapa
    assert len(repo.buscar_bloqueos_solapados(1, "2026-11-20 07:00", "2026-11-20 09:00")) == 1

    # 2. Solapa parcial posterior: 11:00 a 13:00 -> solapa
    assert len(repo.buscar_bloqueos_solapados(1, "2026-11-20 11:00", "2026-11-20 13:00")) == 1

    # 3. Contenido dentro: 09:00 a 10:00 -> solapa
    assert len(repo.buscar_bloqueos_solapados(1, "2026-11-20 09:00", "2026-11-20 10:00")) == 1

    # 4. Contiguo anterior: 06:00 a 08:00 -> NO solapa
    assert len(repo.buscar_bloqueos_solapados(1, "2026-11-20 06:00", "2026-11-20 08:00")) == 0

    # 5. Contiguo posterior: 12:00 a 14:00 -> NO solapa
    assert len(repo.buscar_bloqueos_solapados(1, "2026-11-20 12:00", "2026-11-20 14:00")) == 0

    # 6. Mismo horario otro sillón: sillon 2 -> NO solapa
    assert len(repo.buscar_bloqueos_solapados(2, "2026-11-20 08:00", "2026-11-20 12:00")) == 0


def test_buscar_bloqueos_solapados_con_excluir_id(repo_con_db):
    repo, _, tenant_id, _, _ = repo_con_db

    b = repo.guardar(
        BloqueoSillon(
            tenant_id=tenant_id,
            sillon_id=1,
            fecha_hora_inicio="2026-11-20 08:00",
            fecha_hora_fin="2026-11-20 12:00",
            motivo="Mantenimiento",
        )
    )

    # Excluyendo b.id no reporta solapamiento
    assert len(repo.buscar_bloqueos_solapados(1, "2026-11-20 09:00", "2026-11-20 11:00", excluir_bloqueo_id=b.id)) == 0


def test_listar_bloqueos_con_filtros(repo_con_db):
    repo, _, tenant_id, _, _ = repo_con_db

    repo.guardar(BloqueoSillon(tenant_id=tenant_id, sillon_id=1, fecha_hora_inicio="2026-11-20 08:00", fecha_hora_fin="2026-11-20 12:00", motivo="A"))
    repo.guardar(BloqueoSillon(tenant_id=tenant_id, sillon_id=2, fecha_hora_inicio="2026-11-21 08:00", fecha_hora_fin="2026-11-21 12:00", motivo="B"))
    repo.guardar(BloqueoSillon(tenant_id=tenant_id, sillon_id=1, fecha_hora_inicio="2026-11-25 08:00", fecha_hora_fin="2026-11-25 12:00", motivo="C"))

    # Filtrar por sillon_id
    assert len(repo.listar(sillon_id=1)) == 2
    assert len(repo.listar(sillon_id=2)) == 1

    # Filtrar por rango de fechas
    assert len(repo.listar(fecha_desde="2026-11-20", fecha_hasta="2026-11-21")) == 2
    assert len(repo.listar(fecha_desde="2026-11-24", fecha_hasta="2026-11-30")) == 1


def test_eliminar_bloqueo(repo_con_db):
    repo, _, tenant_id, _, _ = repo_con_db

    b = repo.guardar(
        BloqueoSillon(
            tenant_id=tenant_id,
            sillon_id=1,
            fecha_hora_inicio="2026-11-20 08:00",
            fecha_hora_fin="2026-11-20 12:00",
            motivo="Eliminar",
        )
    )
    assert repo.eliminar(b.id) is True
    assert repo.obtener_por_id(b.id) is None
    assert repo.eliminar(9999) is False


def test_aislamiento_multitenant_bloqueos(repo_con_db):
    repo_t1, conn, t1_id, t2_id, _ = repo_con_db
    repo_t2 = RepositorioBloqueosSqlite(conn, tenant_id=t2_id)

    b_t1 = repo_t1.guardar(
        BloqueoSillon(
            tenant_id=t1_id,
            sillon_id=1,
            fecha_hora_inicio="2026-11-20 08:00",
            fecha_hora_fin="2026-11-20 12:00",
            motivo="Tenant 1",
        )
    )

    # Tenant 2 no puede verlo ni eliminarlo
    assert repo_t2.obtener_por_id(b_t1.id) is None
    assert len(repo_t2.listar()) == 0
    assert repo_t2.eliminar(b_t1.id) is False
