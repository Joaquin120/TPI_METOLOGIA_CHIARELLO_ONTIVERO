"""Tests de integración para el Repositorio de Lista de Espera sobre SQLite (TDD task 1.2)."""

import sqlite3
import pytest

from src.domain.models import EntradaListaEspera, EstadoListaEspera
from src.domain.puertos import PuertoListaEspera
from src.infrastructure.database import abrir_conexion, migrar
from src.infrastructure.seed import TENANT_DEFECTO, sembrar_datos_iniciales
from src.repositories.lista_espera_sqlite import RepositorioListaEsperaSqlite


@pytest.fixture
def conexion_db(tmp_path) -> sqlite3.Connection:
    """Crea una base de datos SQLite con todas las migraciones y seed aplicado."""
    ruta = tmp_path / "test_lista_espera_repo.db"
    conexion = abrir_conexion(ruta)
    migrar(conexion)
    sembrar_datos_iniciales(conexion)
    conexion.execute("INSERT OR IGNORE INTO tenant (id, nombre) VALUES (2, 'Clínica Dos')")
    conexion.commit()
    return conexion


def test_repositorio_implementa_puerto(conexion_db: sqlite3.Connection) -> None:
    repo = RepositorioListaEsperaSqlite(conexion=conexion_db, tenant_id=1)
    assert isinstance(repo, PuertoListaEspera)


def test_guardar_y_obtener_por_id(conexion_db: sqlite3.Connection) -> None:
    repo = RepositorioListaEsperaSqlite(conexion=conexion_db, tenant_id=1)
    entrada = EntradaListaEspera(
        paciente_nombre="Carlos Gardel",
        paciente_telefono="+5491112345678",
        fecha_deseada="2026-11-20",
        motivo="Limpieza y revisión",
        profesional_nombre="Dr. Perez",
        franja_horaria="MAÑANA",
    )
    guardada = repo.guardar(entrada)
    assert guardada.id is not None
    assert guardada.tenant_id == 1
    assert guardada.estado == EstadoListaEspera.PENDIENTE
    assert guardada.creado_en is not None

    recuperada = repo.obtener_por_id(guardada.id)
    assert recuperada is not None
    assert recuperada.id == guardada.id
    assert recuperada.paciente_nombre == "Carlos Gardel"
    assert recuperada.profesional_nombre == "Dr. Perez"


def test_aislamiento_multitenant(conexion_db: sqlite3.Connection) -> None:
    repo_t1 = RepositorioListaEsperaSqlite(conexion=conexion_db, tenant_id=1)
    repo_t2 = RepositorioListaEsperaSqlite(conexion=conexion_db, tenant_id=2)

    entrada = EntradaListaEspera(
        paciente_nombre="Paciente T1",
        paciente_telefono="+5491100001111",
        fecha_deseada="2026-11-20",
        motivo="Consulta",
    )
    guardada = repo_t1.guardar(entrada)

    # El tenant 2 no debe poder acceder ni listar la entrada del tenant 1
    assert repo_t2.obtener_por_id(guardada.id) is None
    assert len(repo_t2.listar()) == 0


def test_actualizar_estado(conexion_db: sqlite3.Connection) -> None:
    repo = RepositorioListaEsperaSqlite(conexion=conexion_db, tenant_id=1)
    entrada = repo.guardar(
        EntradaListaEspera(
            paciente_nombre="Paciente A",
            paciente_telefono="+5491122223333",
            fecha_deseada="2026-11-21",
            motivo="Control",
        )
    )

    from dataclasses import replace

    actualizada = replace(entrada, estado=EstadoListaEspera.CANCELADO)
    res = repo.actualizar(actualizada)
    assert res.estado == EstadoListaEspera.CANCELADO

    recuperada = repo.obtener_por_id(entrada.id)
    assert recuperada is not None
    assert recuperada.estado == EstadoListaEspera.CANCELADO


def test_buscar_candidatos_orden_fifo(conexion_db: sqlite3.Connection) -> None:
    repo = RepositorioListaEsperaSqlite(conexion=conexion_db, tenant_id=1)

    # Insertamos 3 entradas en diferentes momentos simulados
    e1 = repo.guardar(
        EntradaListaEspera(
            paciente_nombre="Primero",
            paciente_telefono="+5491111111111",
            fecha_deseada="2026-11-22",
            motivo="Urgencia",
            profesional_nombre="Dra. Lopez",
        )
    )
    e2 = repo.guardar(
        EntradaListaEspera(
            paciente_nombre="Segundo",
            paciente_telefono="+5491122222222",
            fecha_deseada="2026-11-22",
            motivo="Consulta",
            profesional_nombre="Dra. Lopez",
        )
    )
    # Uno para otro profesional
    repo.guardar(
        EntradaListaEspera(
            paciente_nombre="Otro Profesional",
            paciente_telefono="+5491133333333",
            fecha_deseada="2026-11-22",
            motivo="Extracción",
            profesional_nombre="Dr. Gómez",
        )
    )

    candidatos = repo.buscar_candidatos(fecha="2026-11-22", profesional_nombre="Dra. Lopez")
    assert len(candidatos) == 2
    assert candidatos[0].id == e1.id
    assert candidatos[1].id == e2.id


def test_buscar_candidatos_excluye_no_pendientes_y_otras_fechas(
    conexion_db: sqlite3.Connection,
) -> None:
    repo = RepositorioListaEsperaSqlite(conexion=conexion_db, tenant_id=1)

    # Entrada para otra fecha
    repo.guardar(
        EntradaListaEspera(
            paciente_nombre="Otra Fecha",
            paciente_telefono="+5491144445555",
            fecha_deseada="2026-11-30",
            motivo="Control",
        )
    )
    # Entrada cancelada
    e_cancelada = repo.guardar(
        EntradaListaEspera(
            paciente_nombre="Cancelado",
            paciente_telefono="+5491177778888",
            fecha_deseada="2026-11-25",
            motivo="Control",
        )
    )
    from dataclasses import replace

    repo.actualizar(replace(e_cancelada, estado=EstadoListaEspera.CANCELADO))

    # Entrada pendiente para la fecha
    e_ok = repo.guardar(
        EntradaListaEspera(
            paciente_nombre="Pendiente OK",
            paciente_telefono="+5491199990000",
            fecha_deseada="2026-11-25",
            motivo="Consulta",
        )
    )

    candidatos = repo.buscar_candidatos(fecha="2026-11-25")
    assert len(candidatos) == 1
    assert candidatos[0].id == e_ok.id
