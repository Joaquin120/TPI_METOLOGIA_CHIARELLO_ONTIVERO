# Tasks

> **Gate CRITICO (gobernanza `C-02`)**: ninguna tarea de código (grupo 2 en adelante) se ejecuta sin aprobación humana explícita del `design.md` — en particular de la sección *Decisiones abiertas* (`DP-02`, `DP-06`). Spec First (regla dura 1): esta especificación ya existe en `specs/persistir-turnos/spec.md`.

## 0. Aprobación del diseño

- [x] 0.1 Presentar `design.md` (Decisiones abiertas: `DP-02` sqlite3 stdlib + `DP-06` `INTEGER AUTOINCREMENT` provisorios) al usuario y registrar su aprobación explícita — verificación: el usuario confirma por escrito "aprobar" o pide cambios (si pide cambios, revisar `design.md` y `tasks.md` antes de continuar); sin ese visto bueno no se abre ningún archivo bajo `backend/src/` ni `backend/tests/`.
  - **Aprobado por escrito (2026-11-03)**: `DP-02` → **sqlite3 stdlib + `001_init.sql` (provisorio)**; `DP-06` → **`INTEGER AUTOINCREMENT` + timestamps ISO-8601 en TEXT, sin auditoría ni soft-delete (provisorio)**.
- [x] 0.2 Confirmar con el usuario el corte de alcance `C-02`/`C-03` sobre `src/repositories/` e `src/infrastructure/` (design D1) y la desviación de 1 línea en `test_estados_turno.py` (`_sembrar`, design D2) — verificación: respuesta del usuario registrada en el reporte de la sesión; cualquier "no" obliga a rediseñar antes de implementar.
  - **Aprobado por escrito (2026-11-03)**: corte de alcance **confirmado tal cual D1** (C-02 crea `src/repositories/` e `src/infrastructure/`; C-03 se queda en `src/api/` + composición) · desviación de 1 línea en `_sembrar` **aceptada**.

## 1. Infraestructura de persistencia (sin tocar el dominio)

- [x] 1.1 Crear los paquetes `backend/src/infrastructure/` y `backend/src/repositories/` con sus `__init__.py` y verificar que la suite siga en verde — verificación: `cd backend && pytest` → 25 verdes.
- [x] 1.2 Escribir `backend/src/infrastructure/migrations/001_init.sql` (tablas `tenant`, `profesional`, `sillon`, `paciente`, `turno` con `tenant_id`, FKs, `CHECK (estado IN (...))`, `fecha_hora_inicio`/`fecha_hora_fin`, índices `(tenant_id, fecha_hora_inicio)` y únicos provisorios `(tenant_id, nombre)`) más un runner idempotente con `schema_migrations` — verificación: test nuevo `test_persistencia_esquema.py::test_esquema_001_crea_las_cinco_tablas` crea una base temporal, la migra dos veces y las tablas/índices existen sin duplicar.
- [x] 1.3 Implementar la resolución de la ruta de la base por variable de entorno `TURNO_DB_PATH` con default documentado (design D7, `D-05`, regla dura 6) — verificación: test `test_persistencia_config.py::test_ruta_de_la_base_sale_del_entorno` apunta la variable a un archivo de `tmp_path` y confirma que esa base se usa; ningún literal de ruta sensible en el código.
- [x] 1.4 Implementar la semilla sintética e idempotente (1 tenant `Clínica Ejemplo`, 2 profesionales `Dr. Ejemplo`/`Dra. Ejemplo`, 2 sillones `Sillón 1`/`Sillón 2`; regla dura 3 / `RN-06`) — verificación: tests `test_persistencia_seed.py::test_seed_carga_un_tenant_dos_profesionales_y_dos_sillones` y `::test_seed_es_idempotente` pasan en una base temporal.
- [x] 1.5 Agregar `*.db`/`*.sqlite` a `.gitignore` para que ninguna base de datos se commitee — verificación: `git status --porcelain` no muestra archivos de base de datos.

## 2. Puerto de repositorio e inyección en el servicio de dominio

- [x] 2.1 Definir el puerto `PuertoTurnos` (Protocol de la stdlib en `backend/src/domain/`, diseño D1) con los métodos `guardar`, `listar`, `actualizar`, `agregar` y `buscar_activos_solapables` — verificación: `cd backend && python -c "from src.domain.puertos import PuertoTurnos"` y `pytest` → 25 verdes (el dominio no importa `sqlite3` ni SQL: revisión de imports en `src/domain/`).
- [x] 2.2 Implementar `RepositorioTurnosEnMemoria` (`backend/src/repositories/`) con la misma semántica de la lista actual, incluido el guard único `ESTADOS_ACTIVOS` y el criterio semiabierto `_hay_solapamiento` — verificación: `pytest tests/test_turnos.py tests/test_estados_turno.py` → los 25 tests existentes siguen verdes sin modificar escenarios ni aserciones.
- [x] 2.3 Inyectar el repositorio en `ServicioTurnos.__init__(repositorio=None)` (default en memoria, diseño D2): eliminar `self._turnos` y delegar `agendar_turno`, `turnos_registrados` y `_transicionar` en el puerto; cambiar la única línea del helper `_sembrar` (`test_estados_turno.py:86`) a `servicio._repositorio.agregar(turno)` — verificación: `cd backend && pytest` → 25 verdes; grep `self._turnos` en `src/` no devuelve resultados; `test_turnos.py` intacto (8 tests).
- [x] 2.4 Tests unitarios del comportamiento de dominio sobre el puerto (paridad de excepciones `SolapamientoProfesionalError`/`SolapamientoSillonError`/`TransicionInvalidaError` y de `turnos_registrados`) — verificación: `pytest tests/test_persistencia_puerto.py` en verde y `pytest` completo en verde.

## 3. Repositorio SQLite y tests de integración (SQLite real, nunca mockeado)

- [x] 3.1 Implementar `RepositorioTurnosSqlite` con el mapeo dominio↔fila (texto ISO `fecha_hora_inicio`/`fecha_hora_fin` ↔ `fecha`+`hora_*`, `estado` TEXT, `id` opcional) y `guardar`/`listar`/`actualizar` filtrando siempre por `tenant_id` (design D3/D6, `RN-05`, regla dura 8) — verificación: tests `test_persistencia_turnos.py::test_alta_queda_persistida_y_consultable_desde_otra_conexión` y `::test_turnos_se_recuperan_completos` pasan contra un archivo SQLite real de `tmp_path`.
- [x] 3.2 Implementar `buscar_activos_solapables` con `tenant_id` + `estado IN (<generado desde ESTADOS_ACTIVOS>)` + criterio semiabierto `fecha_hora_inicio < :nuevo_fin AND fecha_hora_fin > :nuevo_inicio` (design D5; `RN-04`, `D-07`, checklist de `.atl/skills/domain-state-matrix-validator.md`) — verificación: tests `test_cancelado_no_bloquea_via_bd`, `test_completado_no_bloquea_via_bd`, `test_turnos_contiguos_via_bd` y `test_solape_invertido_via_bd` pasan.
- [x] 3.3 Mantener la doble validación y la precedencia RN-09 en el servicio sobre los candidatos SQL (design D5) — verificación: tests `test_conflicto_profesional_via_bd` → `SolapamientoProfesionalError` y `test_conflicto_sillon_via_bd` → `SolapamientoSillonError`, ambos en verde.
- [x] 3.4 Implementar los repositorios de recursos (`RepositorioProfesionales`, `RepositorioSillones`, `RepositorioPacientes`) con resolución de recursos por nombre dentro del tenant y *upsert* de paciente (design D6) — verificación: tests `test_resolucion_de_recursos_dentro_del_tenant` y `test_paciente_se_crea_por_nombre` en verde.
- [x] 3.5 Tests de aislamiento por tenant: un turno del tenant A no se ve desde el tenant B y un solapamiento no se detecta contra turnos de otro tenant (`RN-05`) — verificación: tests `test_turno_no_visible_desde_otro_tenant` y `test_solapamiento_no_cruza_tenants` en verde con dos bases/repositorios de tenant distintos sobre SQLite real.
- [x] 3.6 Tests de configuración y semilla contra la base real (los escenarios de env y seed de `specs/persistir-turnos/spec.md`) — verificación: `cd backend && pytest tests/test_persistencia_config.py tests/test_persistencia_seed.py` en verde.

## 4. Verificación final (reglas duras)

- [x] 4.1 Correr la suite completa: `cd backend && pytest` → 100% en verde, incluidos los 25 tests previos sin modificar sus escenarios ni aserciones (regla dura 4).
- [x] 4.2 Correr `cd backend && pytest --cov=src` → sin regresión de cobertura sobre `domain/`, `repositories/` e `infrastructure/`; reportar el porcentaje en el resumen del change.
- [x] 4.3 Revisar el checklist de `.atl/skills/domain-state-matrix-validator.md` aplicado a `C-02`: filtro gobernado por un solo guard `ESTADOS_ACTIVOS` en ambas ramas, `_hay_solapamiento`/SQL semiabierto, turnos cancelados conservados como historial, máquina de estados intacta y sus 3 escenarios siguen verdes — verificación: checklist completo tildado en el reporte.
- [x] 4.4 Revisar reglas duras de `AGENTS.md` sobre el resultado: spec first (2→8), doble validación en SQL, solo datos sintéticos (`Dr. Ejemplo`, `Paciente Ficticio`), suite verde, SQLite real sin mocks, sin secretos en el repo, semiabierto, `tenant_id` en toda consulta — verificación: revisión manual con evidencia de cada punto en el reporte.
- [x] 4.5 Re-validar el change: `openspec validate c-02-persistencia-sqlite --strict` → 0 errores, 0 warnings (keywords `GIVEN`/`WHEN`/`THEN`/`AND` en todos los escenarios) — verificación: salida del comando en 0/0.

## Workflow follow-up

- Commitear únicamente si el usuario lo pide, con Conventional Commits (regla dura 9); nunca `git push`, builds ni deploys sin confirmación explícita (regla dura 10).
- Al cerrar: `/opsx:archive c-02-persistencia-sqlite` y marcar el checkbox `[x]` de `C-02` en `CHANGES.md` junto con la fecha de archivado.
- Después de archivar, `GATE 2` habilita `C-03 capa-api-desacoplada` (no arrancarlo desde este change).
