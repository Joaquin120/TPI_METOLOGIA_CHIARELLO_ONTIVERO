# Proposal

## Why

`ServicioTurnos` guarda los turnos en la lista en memoria `self._turnos`: cada proceso arranca vacío, no hay aislamiento por tenant (RN-05) ni integridad referencial, y la validación de solapamiento recorre una lista Python en lugar de consultar una fuente persistente. Sin persistencia real no hay agenda que operar al día siguiente ni base sobre la cual construir la API desacoplada (`C-03`), y el camino crítico MVP (`C-01 → C-02 → C-03`) queda detenido en `GATE 1`.

## What Changes

- Migración 001 sobre **SQLite** (`D-04`, desarrollo y pruebas): tablas `tenant`, `profesional`, `sillon`, `paciente` y `turno` con `tenant_id`, claves foráneas, `estado` como valor enumerado y los campos `fecha_hora_inicio` / `fecha_hora_fin` (intervalo semiabierto `[inicio, fin)`, `D-07`).
- Cuatro repositorios — `RepositorioTurnos`, `RepositorioProfesionales`, `RepositorioSillones`, `RepositorioPacientes` — **siempre filtrando por `tenant_id`** (RN-05, regla dura 8): la ventana de tenant se fija en el contexto de la operación y toda consulta la aplica (arquitectura §5.3).
- `ServicioTurnos` **deja de guardar en `self._turnos`** y recibe el repositorio por inyección; su comportamiento visible (doble validación de profesional y sillón, matriz RN-03, `ESTADOS_ACTIVOS`, excepciones de dominio) **no cambia**.
- La selección de candidatos a solapamiento se traslada a SQL: `tenant_id` + `estado IN (estados activos)` + criterio semiabierto `fecha_hora_inicio < :nuevo_fin AND fecha_hora_fin > :nuevo_inicio` + (`profesional` OR `sillon`); el filtro de bloqueo sigue gobernado por un único guard `ESTADOS_ACTIVOS` (RN-04), de modo que **un turno cancelado o completado no bloquea vía BD**.
- Configuración de la ruta de la base **por variables de entorno** (`.env`, `D-05`, regla dura 6): sin secretos ni rutas hardcodeadas sensibles en el repo.
- Seed sintético e idempotente: 1 tenant, 2 profesionales y 2 sillones con datos ficticios (`Clínica Ejemplo`, `Dr. Ejemplo`, `Sillón 1`; RN-06, regla dura 3).
- Tests de integración contra **SQLite real** (nunca mockeada, regla dura 5): alta → consulta persistida, aislamiento por tenant, turnos cancelados no bloquean vía BD, turnos contiguos vía BD, doble validación vía BD. La suite existente (25 tests) debe seguir **100% verde** sin modificaciones de escenarios ni aserciones (regla dura 4).
- **Sin cambios** en `backend/src/domain/` más allá de las extensiones aditivas mínimas descritas en `design.md` (sin cambio de comportamiento): sin API HTTP (es `C-03`), sin resolución de `PA-13`, `DP-01`, `DP-03`, `DP-04`.

## Capabilities

### New Capabilities

- `persistir-turnos`: almacenamiento durable e aislado por tenant de los turnos y sus recursos — alta consultable tras reabrir la base, invisibilidad entre tenants (RN-05), validación de solapamiento ejecutada contra la base con turnos activos y intervalos semiabiertos (RN-04 / D-07), configuración de la base por variables de entorno (D-05) y datos iniciales sintéticos (RN-06).

### Modified Capabilities

_(ninguna)_

Los requisitos de `crear-turno` y `gestionar-estados-turno` siguen vigentes sin cambios de texto: solo cambia *dónde* se ejecutan (la selección de candidatos pasa de una lista Python a consultas SQL), no *qué* observable produce el sistema. La capacidad nueva absorbe los requisitos nuevos de persistencia y aislamiento.

## Impact

- **Dominio**: `backend/src/domain/services.py` (`ServicioTurnos` inyecta un repositorio; `agendar_turno`, `confirmar`, `cancelar`, `completar`, `turnos_registrados` conservan firma y comportamiento), `backend/src/domain/models.py` (posibles campos opcionales aditivos `id`, sin cambiar defaults ni aserciones existentes). `exceptions.py` intacto.
- **Nuevo código de soporte**: puerto de repositorio en el dominio; adaptadores SQLite (y uno en memoria para los tests unitarios existentes) en `src/repositories/`; configuración/semilla/migración en `src/infrastructure/` (estructura objetivo `architecture.md` §9).
- **Dependencias**: se propone **cero dependencias nuevas** en `backend/requirements.txt` (sqlite3 de la stdlib como valor provisorio — ver decisiones abiertas). Si se elige SQLAlchemy/Alembic, el change debe revisarse antes de implementar.
- **Tests**: tests nuevos de integración en `backend/tests/` (carpeta nueva o `test_persistencia*.py`); los 25 tests existentes conservan escenarios y aserciones.
- **Sin impacto** en API HTTP, frontend, notificaciones ni en los specs vigentes `crear-turno` / `gestionar-estados-turno`. No se tocan `CHANGES.md`, `AGENTS.md` ni `CLAUDE.md`.

## Gobernanza y decisiones abiertas

- **C-02 es un change de gobernanza CRITICO**: esta propuesta es solo planificación. **Se requiere aprobación humana explícita antes de escribir cualquier código** (ninguna tarea de `tasks.md` se ejecuta sin ese visto bueno).
- **`DP-02` (BD y ORM/migraciones de producción) NO se resuelve aquí**: este change solo materializa el entorno de desarrollo/pruebas de `D-04`. Se deja en superficie, no se decide en silencio — el valor provisorio elegido para `C-02` (sqlite3 stdlib + script de migración 001) queda expuesto para aprobación en `design.md §Decisiones abiertas`.
- **`DP-06` (tipo de identificadores, timestamps, auditoría, borrado lógico) NO se resuelve aquí**: el diseño de tablas de la migración 001 usa un tipo de identificador **provisorio** claramente marcado, revisable cuando `DP-06`/`PA-16` se respondan.
- `DP-01`, `DP-03`, `DP-04` pertenecen a `C-03`/`C-04` y quedan intactos; `PA-13` (estado inicial del alta) sigue abierta.
- Conventional Commits para el eventual commit del change; builds, deploys y `git push` no se ejecutan sin pedir (reglas duras 9 y 10).
