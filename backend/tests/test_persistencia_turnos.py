"""Pruebas de persistencia e integración contra SQLite real (design D8, D-04).

Cubre todos los escenarios descritos en `specs/persistir-turnos/spec.md`.
Regla dura 5: SQLite real en archivos temporales (tmp_path), NUNCA mockeado.
Regla dura 3 / RN-06: únicamente datos sintéticos.
Regla dura 8 / RN-05: aislamiento estricto por tenant.
"""

import pytest

from src.domain.exceptions import (
    SolapamientoProfesionalError,
    SolapamientoSillonError,
)
from src.domain.models import CANCELADO, COMPLETADO, Profesional, Sillon, Turno
from src.domain.services import ServicioTurnos
from src.infrastructure.database import abrir_conexion, migrar
from src.infrastructure.seed import sembrar_datos_iniciales
from src.repositories.recursos import (
    RepositorioPacientes,
    RepositorioProfesionales,
    RepositorioSillones,
)
from src.repositories.turnos_sqlite import RepositorioTurnosSqlite


def _obtener_tenant_id(conexion, nombre="Clínica Ejemplo") -> int:
    """Helper para obtener el id del tenant sembrado."""
    fila = conexion.execute("SELECT id FROM tenant WHERE nombre = ?", (nombre,)).fetchone()
    return fila[0] if isinstance(fila, (tuple, list)) else fila["id"]


def test_alta_queda_persistida_y_consultable_desde_otra_conexion(tmp_path) -> None:
    """Scenario: El turno agendado se recupera desde la base (Camino Feliz)."""
    ruta = tmp_path / "alta_consultable.db"
    conexion1 = abrir_conexion(str(ruta))
    migrar(conexion1)
    sembrar_datos_iniciales(conexion1)
    tenant_id = _obtener_tenant_id(conexion1)

    repo1 = RepositorioTurnosSqlite(conexion1, tenant_id=tenant_id)
    servicio = ServicioTurnos(repositorio=repo1)

    prof = Profesional(nombre="Dr. Ejemplo")
    sil = Sillon(nombre="Sillón 1")
    turno_creado = servicio.agendar_turno(
        paciente="Paciente Ficticio",
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional=prof,
        sillon=sil,
    )
    conexion1.close()

    # Consulta desde una conexión nueva sobre la misma base
    conexion2 = abrir_conexion(str(ruta))
    try:
        repo2 = RepositorioTurnosSqlite(conexion2, tenant_id=tenant_id)
        turnos = repo2.listar()
        assert len(turnos) == 1
        recuperado = turnos[0]
        assert recuperado.id == turno_creado.id
        assert recuperado.profesional.nombre == "Dr. Ejemplo"
        assert recuperado.sillon.nombre == "Sillón 1"
        assert recuperado.paciente == "Paciente Ficticio"
        assert recuperado.fecha == "2026-11-01"
        assert recuperado.hora_inicio == "10:00"
        assert recuperado.hora_fin == "10:30"
        assert recuperado.estado == "CONFIRMADO"
    finally:
        conexion2.close()


def test_turnos_se_recuperan_ordenados_y_completos_tras_reabrir_la_base(tmp_path) -> None:
    """Scenario: Los turnos se recuperan ordenados y completos tras reabrir la base (Camino Feliz)."""
    ruta = tmp_path / "turnos_ordenados.db"
    conexion = abrir_conexion(str(ruta))
    migrar(conexion)
    sembrar_datos_iniciales(conexion)
    tenant_id = _obtener_tenant_id(conexion)

    repo = RepositorioTurnosSqlite(conexion, tenant_id=tenant_id)
    servicio = ServicioTurnos(repositorio=repo)

    servicio.agendar_turno(
        paciente="Paciente Ficticio 1",
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional=Profesional(nombre="Dr. Ejemplo"),
        sillon=Sillon(nombre="Sillón 1"),
    )
    servicio.agendar_turno(
        paciente="Paciente Ficticio 2",
        fecha="2026-11-01",
        hora_inicio="11:00",
        hora_fin="11:30",
        profesional=Profesional(nombre="Dr. Ejemplo"),
        sillon=Sillon(nombre="Sillón 1"),
    )
    conexion.close()

    # Reabrir con nueva conexión e instancia de servicio
    conexion_reabierta = abrir_conexion(str(ruta))
    try:
        repo_reabierto = RepositorioTurnosSqlite(conexion_reabierta, tenant_id=tenant_id)
        servicio_nuevo = ServicioTurnos(repositorio=repo_reabierto)
        registrados = servicio_nuevo.turnos_registrados()

        assert len(registrados) == 2
        assert registrados[0].hora_inicio == "10:00"
        assert registrados[0].paciente == "Paciente Ficticio 1"
        assert registrados[1].hora_inicio == "11:00"
        assert registrados[1].paciente == "Paciente Ficticio 2"
    finally:
        conexion_reabierta.close()


def test_turno_no_es_visible_desde_otro_tenant(tmp_path) -> None:
    """Scenario: Un turno de un tenant no es visible desde otro tenant (RN-05)."""
    ruta = tmp_path / "aislamiento_tenant.db"
    conexion = abrir_conexion(str(ruta))
    migrar(conexion)
    sembrar_datos_iniciales(conexion)
    tenant_1_id = _obtener_tenant_id(conexion, "Clínica Ejemplo")

    # Crear un segundo tenant
    conexion.execute("INSERT INTO tenant (nombre) VALUES ('Clínica Secundaria')")
    conexion.commit()
    tenant_2_id = _obtener_tenant_id(conexion, "Clínica Secundaria")

    repo1 = RepositorioTurnosSqlite(conexion, tenant_id=tenant_1_id)
    servicio_tenant_1 = ServicioTurnos(repositorio=repo1)

    servicio_tenant_1.agendar_turno(
        paciente="Paciente Tenant 1",
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional=Profesional(nombre="Dr. Ejemplo"),
        sillon=Sillon(nombre="Sillón 1"),
    )

    repo2 = RepositorioTurnosSqlite(conexion, tenant_id=tenant_2_id)
    servicio_tenant_2 = ServicioTurnos(repositorio=repo2)

    try:
        assert len(servicio_tenant_1.turnos_registrados()) == 1
        assert len(servicio_tenant_2.turnos_registrados()) == 0
    finally:
        conexion.close()


def test_solapamiento_no_se_detecta_contra_turnos_de_otro_tenant(tmp_path) -> None:
    """Scenario: Un solapamiento no se detecta contra turnos de otro tenant (RN-05)."""
    ruta = tmp_path / "solapamiento_inter_tenant.db"
    conexion = abrir_conexion(str(ruta))
    migrar(conexion)
    sembrar_datos_iniciales(conexion)
    tenant_1_id = _obtener_tenant_id(conexion, "Clínica Ejemplo")

    conexion.execute("INSERT INTO tenant (nombre) VALUES ('Clínica Secundaria')")
    conexion.commit()
    tenant_2_id = _obtener_tenant_id(conexion, "Clínica Secundaria")

    repo1 = RepositorioTurnosSqlite(conexion, tenant_id=tenant_1_id)
    repo2 = RepositorioTurnosSqlite(conexion, tenant_id=tenant_2_id)
    servicio_1 = ServicioTurnos(repositorio=repo1)
    servicio_2 = ServicioTurnos(repositorio=repo2)

    try:
        # Tenant 1 agenda de 10:00 a 10:30
        servicio_1.agendar_turno(
            paciente="Paciente Tenant 1",
            fecha="2026-11-01",
            hora_inicio="10:00",
            hora_fin="10:30",
            profesional=Profesional(nombre="Dr. Ejemplo"),
            sillon=Sillon(nombre="Sillón 1"),
        )

        # Tenant 2 agenda en el MISMO intervalo con nombres de recursos idénticos
        turno_tenant_2 = servicio_2.agendar_turno(
            paciente="Paciente Tenant 2",
            fecha="2026-11-01",
            hora_inicio="10:00",
            hora_fin="10:30",
            profesional=Profesional(nombre="Dr. Ejemplo"),
            sillon=Sillon(nombre="Sillón 1"),
        )
        assert turno_tenant_2.estado == "CONFIRMADO"
    finally:
        conexion.close()


def test_turno_cancelado_en_la_base_no_bloquea_la_re_reserva(tmp_path) -> None:
    """Scenario: Un turno cancelado en la base no bloquea la re-reserva (RN-04)."""
    ruta = tmp_path / "cancelado_no_bloquea.db"
    conexion = abrir_conexion(str(ruta))
    migrar(conexion)
    sembrar_datos_iniciales(conexion)
    tenant_id = _obtener_tenant_id(conexion)

    repo = RepositorioTurnosSqlite(conexion, tenant_id=tenant_id)
    servicio = ServicioTurnos(repositorio=repo)

    try:
        turno = servicio.agendar_turno(
            paciente="Paciente Ficticio",
            fecha="2026-11-01",
            hora_inicio="10:00",
            hora_fin="10:30",
            profesional=Profesional(nombre="Dr. Ejemplo"),
            sillon=Sillon(nombre="Sillón 1"),
        )
        servicio.cancelar(turno)

        # Nuevo turno solapado con el cancelado
        nuevo_turno = servicio.agendar_turno(
            paciente="Paciente Ficticio 2",
            fecha="2026-11-01",
            hora_inicio="10:15",
            hora_fin="10:45",
            profesional=Profesional(nombre="Dr. Ejemplo"),
            sillon=Sillon(nombre="Sillón 1"),
        )
        assert nuevo_turno.estado == "CONFIRMADO"
        assert len(servicio.turnos_registrados()) == 2
        estados = [t.estado for t in servicio.turnos_registrados()]
        assert estados == [CANCELADO, "CONFIRMADO"]
    finally:
        conexion.close()


def test_turno_completado_en_la_base_tampoco_bloquea(tmp_path) -> None:
    """Scenario: Un turno completado en la base tampoco bloquea (RN-04)."""
    ruta = tmp_path / "completado_no_bloquea.db"
    conexion = abrir_conexion(str(ruta))
    migrar(conexion)
    sembrar_datos_iniciales(conexion)
    tenant_id = _obtener_tenant_id(conexion)

    repo = RepositorioTurnosSqlite(conexion, tenant_id=tenant_id)
    servicio = ServicioTurnos(repositorio=repo)

    try:
        turno = servicio.agendar_turno(
            paciente="Paciente Ficticio",
            fecha="2026-11-01",
            hora_inicio="10:00",
            hora_fin="10:30",
            profesional=Profesional(nombre="Dr. Ejemplo"),
            sillon=Sillon(nombre="Sillón 1"),
        )
        servicio.completar(turno)

        # Mismo sillón con otro profesional de 10:15 a 10:45
        nuevo_turno = servicio.agendar_turno(
            paciente="Paciente Ficticio 2",
            fecha="2026-11-01",
            hora_inicio="10:15",
            hora_fin="10:45",
            profesional=Profesional(nombre="Dra. Ejemplo"),
            sillon=Sillon(nombre="Sillón 1"),
        )
        assert nuevo_turno.estado == "CONFIRMADO"
        assert len(servicio.turnos_registrados()) == 2
    finally:
        conexion.close()


def test_turnos_contiguos_registrados_via_base_de_datos(tmp_path) -> None:
    """Scenario: Turnos contiguos registrados vía base de datos (D-07)."""
    ruta = tmp_path / "contiguos_bd.db"
    conexion = abrir_conexion(str(ruta))
    migrar(conexion)
    sembrar_datos_iniciales(conexion)
    tenant_id = _obtener_tenant_id(conexion)

    repo = RepositorioTurnosSqlite(conexion, tenant_id=tenant_id)
    servicio = ServicioTurnos(repositorio=repo)

    try:
        servicio.agendar_turno(
            paciente="Paciente Ficticio 1",
            fecha="2026-11-01",
            hora_inicio="10:00",
            hora_fin="10:30",
            profesional=Profesional(nombre="Dr. Ejemplo"),
            sillon=Sillon(nombre="Sillón 1"),
        )
        turno_2 = servicio.agendar_turno(
            paciente="Paciente Ficticio 2",
            fecha="2026-11-01",
            hora_inicio="10:30",
            hora_fin="11:00",
            profesional=Profesional(nombre="Dr. Ejemplo"),
            sillon=Sillon(nombre="Sillón 1"),
        )
        assert turno_2.estado == "CONFIRMADO"
        assert len(servicio.turnos_registrados()) == 2
    finally:
        conexion.close()


def test_solape_invertido_rechazado_via_base_de_datos(tmp_path) -> None:
    """Scenario: Solape invertido rechazado vía base de datos (D-07)."""
    ruta = tmp_path / "solape_invertido.db"
    conexion = abrir_conexion(str(ruta))
    migrar(conexion)
    sembrar_datos_iniciales(conexion)
    tenant_id = _obtener_tenant_id(conexion)

    repo = RepositorioTurnosSqlite(conexion, tenant_id=tenant_id)
    servicio = ServicioTurnos(repositorio=repo)

    try:
        servicio.agendar_turno(
            paciente="Paciente Ficticio 1",
            fecha="2026-11-01",
            hora_inicio="10:00",
            hora_fin="10:30",
            profesional=Profesional(nombre="Dr. Ejemplo"),
            sillon=Sillon(nombre="Sillón 1"),
        )

        with pytest.raises(SolapamientoSillonError):
            servicio.agendar_turno(
                paciente="Paciente Ficticio 2",
                fecha="2026-11-01",
                hora_inicio="09:45",
                hora_fin="10:15",
                profesional=Profesional(nombre="Dra. Ejemplo"),
                sillon=Sillon(nombre="Sillón 1"),
            )
    finally:
        conexion.close()


def test_conflicto_de_profesional_detectado_en_la_base(tmp_path) -> None:
    """Scenario: Conflicto de profesional detectado en la base (RN-09)."""
    ruta = tmp_path / "conflicto_profesional.db"
    conexion = abrir_conexion(str(ruta))
    migrar(conexion)
    sembrar_datos_iniciales(conexion)
    tenant_id = _obtener_tenant_id(conexion)

    repo = RepositorioTurnosSqlite(conexion, tenant_id=tenant_id)
    servicio = ServicioTurnos(repositorio=repo)

    try:
        servicio.agendar_turno(
            paciente="Paciente Ficticio 1",
            fecha="2026-11-01",
            hora_inicio="10:00",
            hora_fin="10:30",
            profesional=Profesional(nombre="Dr. Ejemplo"),
            sillon=Sillon(nombre="Sillón 1"),
        )

        with pytest.raises(SolapamientoProfesionalError):
            servicio.agendar_turno(
                paciente="Paciente Ficticio 2",
                fecha="2026-11-01",
                hora_inicio="10:15",
                hora_fin="10:45",
                profesional=Profesional(nombre="Dr. Ejemplo"),
                sillon=Sillon(nombre="Sillón 2"),
            )
    finally:
        conexion.close()


def test_conflicto_de_sillon_detectado_en_la_base(tmp_path) -> None:
    """Scenario: Conflicto de sillón detectado en la base (RN-09)."""
    ruta = tmp_path / "conflicto_sillon.db"
    conexion = abrir_conexion(str(ruta))
    migrar(conexion)
    sembrar_datos_iniciales(conexion)
    tenant_id = _obtener_tenant_id(conexion)

    repo = RepositorioTurnosSqlite(conexion, tenant_id=tenant_id)
    servicio = ServicioTurnos(repositorio=repo)

    try:
        servicio.agendar_turno(
            paciente="Paciente Ficticio 1",
            fecha="2026-11-01",
            hora_inicio="10:00",
            hora_fin="10:30",
            profesional=Profesional(nombre="Dr. Ejemplo"),
            sillon=Sillon(nombre="Sillón 1"),
        )

        with pytest.raises(SolapamientoSillonError):
            servicio.agendar_turno(
                paciente="Paciente Ficticio 2",
                fecha="2026-11-01",
                hora_inicio="10:15",
                hora_fin="10:45",
                profesional=Profesional(nombre="Dra. Ejemplo"),
                sillon=Sillon(nombre="Sillón 1"),
            )
    finally:
        conexion.close()


def test_resolucion_de_recursos_dentro_del_tenant(tmp_path) -> None:
    """Task 3.4: Los repositorios de recursos resuelven y listan dentro del tenant."""
    ruta = tmp_path / "recursos.db"
    conexion = abrir_conexion(str(ruta))
    migrar(conexion)
    sembrar_datos_iniciales(conexion)
    tenant_id = _obtener_tenant_id(conexion)

    repo_prof = RepositorioProfesionales(conexion, tenant_id)
    repo_sil = RepositorioSillones(conexion, tenant_id)

    try:
        profesionales = repo_prof.listar()
        assert len(profesionales) == 2
        assert {p.nombre for p in profesionales} == {"Dr. Ejemplo", "Dra. Ejemplo"}

        sillones = repo_sil.listar()
        assert len(sillones) == 2
        assert {s.nombre for s in sillones} == {"Sillón 1", "Sillón 2"}

        # Resolución por ID existente
        id_prof = repo_prof.resolver_id("Dr. Ejemplo")
        assert repo_prof.obtener_por_id(id_prof).nombre == "Dr. Ejemplo"

        id_sil = repo_sil.resolver_id("Sillón 1")
        assert repo_sil.obtener_por_id(id_sil).nombre == "Sillón 1"
    finally:
        conexion.close()


def test_paciente_se_crea_por_nombre(tmp_path) -> None:
    """Task 3.4: El repositorio de pacientes realiza upsert por nombre dentro del tenant."""
    ruta = tmp_path / "pacientes.db"
    conexion = abrir_conexion(str(ruta))
    migrar(conexion)
    sembrar_datos_iniciales(conexion)
    tenant_id = _obtener_tenant_id(conexion)

    repo_pacientes = RepositorioPacientes(conexion, tenant_id)

    try:
        id_1 = repo_pacientes.resolver_id("Paciente Ficticio")
        id_2 = repo_pacientes.resolver_id("Paciente Ficticio")
        assert id_1 == id_2
        assert repo_pacientes.obtener_nombre_por_id(id_1) == "Paciente Ficticio"
    finally:
        conexion.close()


def test_actualizar_turno_con_o_sin_id(tmp_path) -> None:
    """Actualizar un turno en SQLite funciona tanto con ID explícito como por coincidencia."""
    ruta = tmp_path / "actualizar_turnos.db"
    conexion = abrir_conexion(str(ruta))
    migrar(conexion)
    sembrar_datos_iniciales(conexion)
    tenant_id = _obtener_tenant_id(conexion)

    repo = RepositorioTurnosSqlite(conexion, tenant_id)

    turno = Turno(
        profesional=Profesional(nombre="Dr. Ejemplo"),
        sillon=Sillon(nombre="Sillón 1"),
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        paciente="Paciente Ficticio",
    )
    repo.agregar(turno)
    guardado = repo.listar()[0]
    assert guardado.id is not None
    assert guardado.estado == "CONFIRMADO"

    # Actualizar sin ID (coincidencia de recursos e intervalo)
    turno_sin_id_modificado = Turno(
        profesional=Profesional(nombre="Dr. Ejemplo"),
        sillon=Sillon(nombre="Sillón 1"),
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        paciente="Paciente Ficticio",
        estado=CANCELADO,
        id=None,
    )
    repo.actualizar(turno_sin_id_modificado)
    assert repo.listar()[0].estado == CANCELADO

    # Actualizar un turno que no existe sin ID no falla
    turno_inexistente = Turno(
        profesional=Profesional(nombre="Dr. Ejemplo"),
        sillon=Sillon(nombre="Sillón 1"),
        fecha="2026-11-02",
        hora_inicio="15:00",
        hora_fin="15:30",
        paciente="Nadie",
        estado=CANCELADO,
        id=None,
    )
    repo.actualizar(turno_inexistente)
    conexion.close()


def test_obtener_recursos_inexistentes_devuelve_none(tmp_path) -> None:
    """Consultar IDs inexistentes en los repositorios de recursos devuelve None."""
    ruta = tmp_path / "recursos_none.db"
    conexion = abrir_conexion(str(ruta))
    migrar(conexion)
    tenant_id = 1

    repo_prof = RepositorioProfesionales(conexion, tenant_id)
    repo_sil = RepositorioSillones(conexion, tenant_id)
    repo_pac = RepositorioPacientes(conexion, tenant_id)

    assert repo_prof.obtener_por_id(999) is None
    assert repo_sil.obtener_por_id(999) is None
    assert repo_pac.obtener_nombre_por_id(999) is None
    conexion.close()


# ---------------------------------------------------------------------------
# C-05: Task 1.2 - RepositorioTurnosSqlite: obtener_por_id y listar con filtros
# ---------------------------------------------------------------------------


def test_repositorio_obtener_por_id_existente_e_inexistente(tmp_path) -> None:
    """Task 1.2: obtener_por_id devuelve el turno del tenant o None si no existe o es de otro tenant."""
    ruta = tmp_path / "repo_obtener_id.db"
    conexion = abrir_conexion(str(ruta))
    migrar(conexion)
    sembrar_datos_iniciales(conexion)
    tenant1 = _obtener_tenant_id(conexion)

    # Crear tenant 2
    cur = conexion.execute("INSERT INTO tenant (nombre) VALUES ('Clínica Dos')")
    tenant2 = cur.lastrowid
    conexion.commit()

    repo1 = RepositorioTurnosSqlite(conexion, tenant_id=tenant1)
    repo2 = RepositorioTurnosSqlite(conexion, tenant_id=tenant2)

    t1 = repo1.guardar(
        Turno(
            profesional=Profesional(nombre="Dr. Ejemplo"),
            sillon=Sillon(nombre="Sillón 1"),
            fecha="2026-11-01",
            hora_inicio="10:00",
            hora_fin="10:30",
            paciente="Paciente Uno",
        )
    )

    # Recuperar existente
    recuperado = repo1.obtener_por_id(t1.id)
    assert recuperado is not None
    assert recuperado.id == t1.id
    assert recuperado.paciente == "Paciente Uno"
    assert recuperado.profesional.nombre == "Dr. Ejemplo"

    # Inexistente
    assert repo1.obtener_por_id(9999) is None

    # Aislamiento por tenant: repo2 no puede obtener el turno de tenant1
    assert repo2.obtener_por_id(t1.id) is None

    conexion.close()


def test_repositorio_listar_con_filtros_combinables(tmp_path) -> None:
    """Task 1.2: listar filtra por fecha, profesional_id y sillon_id con conjunción lógica."""
    ruta = tmp_path / "repo_filtros.db"
    conexion = abrir_conexion(str(ruta))
    migrar(conexion)
    sembrar_datos_iniciales(conexion)
    tenant = _obtener_tenant_id(conexion)

    repo = RepositorioTurnosSqlite(conexion, tenant_id=tenant)
    prof1_id = RepositorioProfesionales(conexion, tenant).resolver_id("Dr. Ejemplo")
    prof2_id = RepositorioProfesionales(conexion, tenant).resolver_id("Dra. Ejemplo")
    sil1_id = RepositorioSillones(conexion, tenant).resolver_id("Sillón 1")
    sil2_id = RepositorioSillones(conexion, tenant).resolver_id("Sillón 2")

    t1 = repo.guardar(
        Turno(
            profesional=Profesional(nombre="Dr. Ejemplo"),
            sillon=Sillon(nombre="Sillón 1"),
            fecha="2026-11-01",
            hora_inicio="09:00",
            hora_fin="09:30",
            paciente="Paciente A",
        )
    )
    t2 = repo.guardar(
        Turno(
            profesional=Profesional(nombre="Dra. Ejemplo"),
            sillon=Sillon(nombre="Sillón 2"),
            fecha="2026-11-01",
            hora_inicio="10:00",
            hora_fin="10:30",
            paciente="Paciente B",
        )
    )
    t3 = repo.guardar(
        Turno(
            profesional=Profesional(nombre="Dr. Ejemplo"),
            sillon=Sillon(nombre="Sillón 2"),
            fecha="2026-11-02",
            hora_inicio="11:00",
            hora_fin="11:30",
            paciente="Paciente C",
        )
    )

    # Sin filtros
    assert len(repo.listar()) == 3

    # Filtro fecha
    res_fecha = repo.listar(fecha="2026-11-01")
    assert [t.id for t in res_fecha] == [t1.id, t2.id]

    # Filtro profesional
    res_prof = repo.listar(profesional_id=prof1_id)
    assert [t.id for t in res_prof] == [t1.id, t3.id]

    # Filtro sillón
    res_sil = repo.listar(sillon_id=sil2_id)
    assert [t.id for t in res_sil] == [t2.id, t3.id]

    # Filtro combinado (fecha + profesional)
    res_comb = repo.listar(fecha="2026-11-01", profesional_id=prof1_id)
    assert [t.id for t in res_comb] == [t1.id]

    # Filtro combinado sin resultados
    assert repo.listar(fecha="2026-11-02", sillon_id=sil1_id) == []

    conexion.close()

