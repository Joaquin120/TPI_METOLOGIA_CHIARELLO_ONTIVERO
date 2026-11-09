"""Pruebas de RepositorioProfesionales y RepositorioSillones (C-06, task 2.1).

Base SQLite REAL en archivo temporal por test: nunca se mockea la base (regla dura 5 / D-04).
Datos siempre sintéticos (regla dura 3 / RN-06).
"""

from src.infrastructure.database import abrir_conexion, migrar
from src.repositories.recursos import (
    RepositorioProfesionales,
    RepositorioSillones,
)


def test_repositorio_profesionales_campos_y_filtrado_activo(tmp_path) -> None:
    """Valida mapeo de matricula/especialidad/activo, filtrado por activo y aislamiento tenant."""
    ruta = tmp_path / "recursos_profesionales.db"
    conexion = abrir_conexion(str(ruta))
    try:
        migrar(conexion)
        # Crear 2 tenants
        conexion.execute("INSERT INTO tenant (nombre) VALUES ('Clínica A')")
        conexion.execute("INSERT INTO tenant (nombre) VALUES ('Clínica B')")
        id_t1 = conexion.execute("SELECT id FROM tenant WHERE nombre = 'Clínica A'").fetchone()[0]
        id_t2 = conexion.execute("SELECT id FROM tenant WHERE nombre = 'Clínica B'").fetchone()[0]

        # Insertar profesionales en Tenant 1
        conexion.execute(
            """
            INSERT INTO profesional (tenant_id, nombre, matricula, especialidad, activo)
            VALUES (?, 'Dr. Activo', 'MP-1234', 'Ortodoncia', 1)
            """,
            (id_t1,),
        )
        conexion.execute(
            """
            INSERT INTO profesional (tenant_id, nombre, matricula, especialidad, activo)
            VALUES (?, 'Dr. Inactivo', 'MP-5678', 'Cirugía', 0)
            """,
            (id_t1,),
        )

        # Insertar profesional en Tenant 2
        conexion.execute(
            """
            INSERT INTO profesional (tenant_id, nombre, matricula, especialidad, activo)
            VALUES (?, 'Dr. Tenant 2', 'MP-9999', 'Periodoncia', 1)
            """,
            (id_t2,),
        )
        conexion.commit()

        repo_t1 = RepositorioProfesionales(conexion, id_t1)

        # 1. listar(solo_activos=True) por defecto
        activos = repo_t1.listar(solo_activos=True)
        assert len(activos) == 1
        assert activos[0].nombre == "Dr. Activo"
        assert activos[0].matricula == "MP-1234"
        assert activos[0].especialidad == "Ortodoncia"
        assert activos[0].activo is True

        # 2. listar(solo_activos=False)
        todos = repo_t1.listar(solo_activos=False)
        assert len(todos) == 2
        nombres = [p.nombre for p in todos]
        assert "Dr. Activo" in nombres
        assert "Dr. Inactivo" in nombres
        inactivo = next(p for p in todos if p.nombre == "Dr. Inactivo")
        assert inactivo.matricula == "MP-5678"
        assert inactivo.especialidad == "Cirugía"
        assert inactivo.activo is False

        # 3. obtener_por_id
        id_inactivo = inactivo.id
        prof_recuperado = repo_t1.obtener_por_id(id_inactivo)
        assert prof_recuperado is not None
        assert prof_recuperado.nombre == "Dr. Inactivo"
        assert prof_recuperado.activo is False
        assert prof_recuperado.matricula == "MP-5678"

        # 4. Aislamiento: repo_t1 no ve profesionales de Tenant 2
        assert all(p.nombre != "Dr. Tenant 2" for p in todos)
        repo_t2 = RepositorioProfesionales(conexion, id_t2)
        assert len(repo_t2.listar()) == 1
        assert repo_t2.listar()[0].nombre == "Dr. Tenant 2"
    finally:
        conexion.close()


def test_repositorio_sillones_campos_y_filtrado_activo(tmp_path) -> None:
    """Valida mapeo de equipamiento/activo, filtrado por activo y aislamiento tenant."""
    ruta = tmp_path / "recursos_sillones.db"
    conexion = abrir_conexion(str(ruta))
    try:
        migrar(conexion)
        # Crear 2 tenants
        conexion.execute("INSERT INTO tenant (nombre) VALUES ('Clínica A')")
        conexion.execute("INSERT INTO tenant (nombre) VALUES ('Clínica B')")
        id_t1 = conexion.execute("SELECT id FROM tenant WHERE nombre = 'Clínica A'").fetchone()[0]
        id_t2 = conexion.execute("SELECT id FROM tenant WHERE nombre = 'Clínica B'").fetchone()[0]

        # Insertar sillones en Tenant 1
        conexion.execute(
            """
            INSERT INTO sillon (tenant_id, nombre, equipamiento, activo)
            VALUES (?, 'Sillón Operativo', 'Turbina LED + Rayos X', 1)
            """,
            (id_t1,),
        )
        conexion.execute(
            """
            INSERT INTO sillon (tenant_id, nombre, equipamiento, activo)
            VALUES (?, 'Sillón Mantenimiento', 'En reparación', 0)
            """,
            (id_t1,),
        )

        # Insertar sillón en Tenant 2
        conexion.execute(
            """
            INSERT INTO sillon (tenant_id, nombre, equipamiento, activo)
            VALUES (?, 'Sillón Tenant 2', 'Básico', 1)
            """,
            (id_t2,),
        )
        conexion.commit()

        repo_t1 = RepositorioSillones(conexion, id_t1)

        # 1. listar(solo_activos=True)
        activos = repo_t1.listar(solo_activos=True)
        assert len(activos) == 1
        assert activos[0].nombre == "Sillón Operativo"
        assert activos[0].equipamiento == "Turbina LED + Rayos X"
        assert activos[0].activo is True

        # 2. listar(solo_activos=False)
        todos = repo_t1.listar(solo_activos=False)
        assert len(todos) == 2
        nombres = [s.nombre for s in todos]
        assert "Sillón Operativo" in nombres
        assert "Sillón Mantenimiento" in nombres
        inactivo = next(s for s in todos if s.nombre == "Sillón Mantenimiento")
        assert inactivo.equipamiento == "En reparación"
        assert inactivo.activo is False

        # 3. obtener_por_id
        id_inactivo = inactivo.id
        sillon_recuperado = repo_t1.obtener_por_id(id_inactivo)
        assert sillon_recuperado is not None
        assert sillon_recuperado.nombre == "Sillón Mantenimiento"
        assert sillon_recuperado.equipamiento == "En reparación"
        assert sillon_recuperado.activo is False

        # 4. Aislamiento: repo_t1 no ve sillones de Tenant 2
        assert all(s.nombre != "Sillón Tenant 2" for s in todos)
        repo_t2 = RepositorioSillones(conexion, id_t2)
        assert len(repo_t2.listar()) == 1
        assert repo_t2.listar()[0].nombre == "Sillón Tenant 2"
    finally:
        conexion.close()

