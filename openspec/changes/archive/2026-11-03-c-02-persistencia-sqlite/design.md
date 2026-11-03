# Design

## Context

- `backend/src/domain/services.py` — `ServicioTurnos` guarda turnos en `self._turnos: list[Turno]`, valida solapamiento recorriendo la lista con `_hay_solapamiento()` (semiabierto, D-07) y el guard único `ESTADOS_ACTIVOS` (RN-04), y aplica transiciones con `_TRANSICIONES` reemplazando la entrada de la lista. Firma pública: `agendar_turno()`, `confirmar()`, `cancelar()`, `completar()`, `turnos_registrados()`.
- `backend/src/domain/models.py` — `Turno` es `@dataclass(frozen=True)` sin `id` ni `tenant_id` (`profesional`, `sillon`, `fecha`, `hora_inicio`, `hora_fin`, `paciente`, `estado="CONFIRMADO"`); `Profesional`/`Sillon` solo tienen `nombre`. `exceptions.py` no se toca.
- `backend/tests/` — 25 tests verdes con cobertura 100% del paquete `src`; el helper `_sembrar()` de `test_estados_turno.py` siembra estados con `servicio._turnos.append(turno)` (línea 86), único acoplamiento al atributo privado que este change retira.
- Specs vigentes `crear-turno` y `gestionar-estados-turno` describen el comportamiento observable que **no cambia**; `.atl/skills/domain-state-matrix-validator.md` exige que el filtro use `ESTADOS_ACTIVOS` gobierne ambas ramas con un solo guard y que "la persistencia del filtro en SQL" sea alcance de `C-02`.
- Restricciones: reglas duras 1 (spec first), 2 (doble validación), 4 (suite verde), 5 (SQLite real, nunca mock), 6 (sin secretos), 7 (semiabierto), 8 (`tenant_id` siempre presente), 3 (datos sintéticos); `D-04` (SQLite dev/pruebas), `D-05` (env), `RN-05`, `RN-06`. Ver `proposal.md — Why`.

## Goals / Non-Goals

**Goals:**

- Migración 001 y cuatro repositorios con aislamiento por `tenant_id` en toda consulta.
- `ServicioTurnos` sin estado de lista: repositorio inyectado, comportamiento observable idéntico.
- Selección de candidatos a solapamiento ejecutada en SQL (tenant + activos + semiabierto + recursos), precedencia RN-09 preservada.
- Config por variables de entorno, seed sintético idempotente, tests de integración contra SQLite real, suite completa en verde.

**Non-Goals:**

- API HTTP, controladores, esquemas Pydantic, factoría de ensamblaje → `C-03`.
- Auth, RBAC y enforcement de tenant en sesión → `C-04`; estrategia física de aislamiento (`DP-03`) → intacta.
- Base/ORM de producción (`DP-02`), identificadores/auditoría definitivos (`DP-06`), concurrencia/transacciones (`DP-05`), reprogramación (`RP-03`), estado inicial del alta (`PA-13`), `DP-01`/`DP-04`.
- Modificar `CHANGES.md`, `AGENTS.md`, `CLAUDE.md` o los specs archivados.

## Decisions

### D1 — Puerto en el dominio, adaptadores en `src/repositories/`, infraestructura en `src/infrastructure/`

El contrato (`PuertoTurnos` / `PuertoRecursos`, `Protocol` de la stdlib) vive en `src/domain/` para que la dependencia apunte hacia adentro (clean-architecture: DIP); `RepositorioTurnosSqlite` (+ `RepositorioTurnosEnMemoria`) van en `src/repositories/`; conexión, migración, config y seed en `src/infrastructure/`. El dominio jamás importa `sqlite3` ni SQL.

- *Alternativa descartada*: poner también el puerto en `src/repositories/` — haría que `ServicioTurnos` importe una capa externa, violando "dominio puro" (`architecture.md` §3).
- *Alternativa descartada*: modelos ORM como entidades de dominio — filtra ORM hacia adentro y prejuzga `DP-02`.
- **Solape de alcance a confirmar**: `CHANGES.md` también lista `src/repositories/` y `src/infrastructure/` en `C-03`; este change los crea porque la persistencia los exige y `C-03` quedará en añadir `src/api/` + composición. Ver reporte/preguntas al usuario.

### D2 — `ServicioTurnos` recibe el repositorio por inyección, con adaptador en memoria por defecto

```python
def __init__(self, repositorio: PuertoTurnos | None = None) -> None:
    self._repositorio = repositorio if repositorio is not None else RepositorioTurnosEnMemoria()
```

- `self._turnos` desaparece; `turnos_registrados()` delega en `repositorio.listar()`; `agendar_turno()` persiste vía `repositorio.guardar()`; `_transicionar()` reemplaza la entrada vía `repositorio.actualizar()` (antes: índice de la lista).
- El default en memoria conserva los 25 tests unitarios **sin base de datos** (`decisions.md` §5.1: el nivel unitario debe correr sin BD ni HTTP) y sin tocar sus escenarios ni aserciones; la integración inyecta el repositorio SQLite.
- *Alternativa descartada*: repositorio obligatorio — rompería `ServicioTurnos()` en los 25 tests, contradiciendo "unitarias existentes sin cambios" de `CHANGES.md`.
- *Alternativa descartada*: mantener `self._turnos` como alias de la lista interna — acoplamiento oculto que enmascararía errores del repositorio.
- **Desviación mínima a aprobar**: `test_estados_turno.py` línea 86 (`_sembrar`) debe pasar de `servicio._turnos.append(turno)` a `servicio._repositorio.agregar(turno)`. Es la única línea de test que cambia; ningún escenario ni aserción se modifica. `test_turnos.py` (8 tests) queda intacto.

### D3 — Identidad provisoria y contexto de tenant

- `Turno`, `Profesional` y `Sillon` ganan un campo **opcional** `id` (`default=None`, aditivo: no cambia construcciones ni igualdades existentes) para que `_transicionar()` pueda localizar la fila y el servicio devuelva el turno con identidad persistente.
- El `tenant_id` **no** se agrega a los modelos de dominio: la ventana de tenant se fija en el repositorio (`Repositorio...(conexion, tenant_id)`) y toda consulta lo aplica — es la forma prevista en `architecture.md` §5.3 y evita prejuzgar `DP-03`.
- Tipo de identificador: **`INTEGER PRIMARY KEY AUTOINCREMENT` provisorio** (ver Decisiones abiertas, `DP-06`).

### D4 — Acceso a datos: `sqlite3` de la stdlib + migración SQL 001 idempotente

- `backend/src/infrastructure/migrations/001_init.sql` con `CREATE TABLE IF NOT EXISTS tenant / profesional / sillon / paciente / turno`, FKs (`REFERENCES`), `CHECK (estado IN ('PENDIENTE','CONFIRMADO','CANCELADO','COMPLETADO'))`, índices `(tenant_id, fecha_hora_inicio)` y únicos provisorios `(tenant_id, nombre)` en `profesional`/`sillon`; un runner mínimo la ejecuta registrándola en `schema_migrations`.
- Tablas: `turno(id, tenant_id, paciente_id, profesional_id, sillon_id, fecha_hora_inicio, fecha_hora_fin, estado)` con `usuario_id` omitido (pendiente `DP-04`/`DP-06`, `data-models` §2.5).
- Cero dependencias nuevas en `requirements.txt`.
- *Alternativa descartada*: SQLAlchemy + Alembic — dependencia nueva y decisión de ORM que pertenece a `DP-02`; además la skill `sqlalchemy-alembic-expert-best-practices-code-review` figura en `AGENTS.md` pero **no está instalada**. Si el humano la prefiere, el design se revisa antes de codear.

### D5 — Solapamiento: candidatos en SQL, precedencia RN-09 en el dominio

`RepositorioTurnos.buscar_activos_solapables(...)` ejecuta (parámetros bound, sin concatenar valores):

```sql
SELECT ... FROM turno
 WHERE tenant_id = :tenant
   AND estado IN (<generado desde ESTADOS_ACTIVOS>)   -- un solo guard, RN-04
   AND (profesional_id = :prof OR sillon_id = :sillon)
   AND fecha_hora_inicio < :nuevo_fin                 -- D-07: [inicio, fin)
   AND fecha_hora_fin     > :nuevo_inicio
 ORDER BY id;
```

El servicio recorre los candidatos con la lógica actual (primero profesional, luego sillón) y lanza `SolapamientoProfesionalError` / `SolapamientoSillonError` — paridad byte a byte de comportamiento, precedencia RN-09 intacta. La cláusula `estado IN` se construye desde `ESTADOS_ACTIVOS` en tiempo de consulta para que la constante de dominio sea la única fuente (checklist de `domain-state-matrix-validator.md`: un solo guard que gobierna ambas ramas; "turnos cancelados no bloquean vía BD").

- *Alternativa descartada*: resolver la precedencia RN-09 dentro del SQL (primero profesional, luego sillón como dos queries) — cambiaría el comportamiento en el caso mixto (conflicto de sillón con un turno anterior y de profesional con uno posterior) que hoy resuelve por orden de inserción, sin cobertura de tests que lo respalde; "sin cambio de comportamiento del dominio" es la restricción rectora.
- El mantiene también el filtro de fecha: la condición de intervalo subsume la igualdad de `fecha` que hacía el loop en memoria.

### D6 — Mapeo dominio ↔ fila

- `fecha` + `hora_inicio`/`hora_fin` ↔ `fecha_hora_inicio`/`fecha_hora_fin` como **texto ISO-8601** (`'YYYY-MM-DD HH:MM'`): la comparación lexicográfica de SQLite coincide con la cronológica (mismo criterio semiabierto), y el repositorio recompone `fecha`/`hora_*` al devolver el `Turno`.
- Recursos: el repositorio resuelve `Profesional(nombre)`/`Sillon(nombre)` a `id` **dentro del tenant** (los tests y el seed garantizan existencia); el `paciente` se hace *upsert* por nombre dentro del tenant (`dni` nullable, pendiente `PA-05`).
- `estado` se persiste como TEXT con el `CHECK` del enum (los modelos de dominio ya lo manejan como `str`, `design D1` de `C-01`).

### D7 — Configuración sin secretos

- `TURNO_DB_PATH` leída con `os.environ` (+ valor por defecto documentado para dev), jamás hardcodeada; las pruebas de integración la apuntan a un archivo temporal de `tmp_path`. Cumple `D-05`/regla 6 sin sumar dependencias (no se agrega `python-dotenv`: la auto-carga de `.env` queda como opción futura, ver Open Questions).
- Archivos `*.db`/`*.sqlite` de desarrollo no se commitean (`.gitignore`); no hay credenciales que ocultar porque SQLite local no las usa.

### D8 — Estrategia de pruebas (reglas duras 4 y 5)

- **Unitarias (existentes, sin cambios de escenario/aserción)**: siguen contra el repositorio en memoria — sin BD.
- **Integración (nuevas, `backend/tests/test_persistencia_turnos.py`)**: base **SQLite real** en archivo temporal por test (`tmp_path` + `TURNO_DB_PATH`), sembrada, nunca mockeada. Cubren los escenarios de `specs/persistir-turnos/spec.md`: alta → consulta desde conexión nueva, aislamiento por tenant, cancelado/completado no bloquean vía BD, contiguos vía BD, solape invertido, doble validación (profesional y sillón), config por entorno, seed idempotente.
- Cierre: `cd backend && pytest` 100% verde y `pytest --cov=src` sin regresión de cobertura (regla dura 4).

## Decisiones abiertas que condicionan la implementación

> **Gobernanza CRITICO**: `C-02` no escribe ninguna línea de código sin aprobación humana explícita de este apartado. No se resuelven en silencio.

| ID | Qué se usa en `C-02` (provisorio) | Alternativa que lo reabre | Qué se pierde si se elige distinto |
|---|---|---|---|
| **`DP-02`** — BD y ORM/migraciones de producción | sqlite3 stdlib + `001_init.sql` (solo dev/pruebas, `D-04`) | SQLAlchemy + Alembic u otro ORM | Reescribir adaptadores y migración; requiere instalar la skill `sqlalchemy-alembic` ausente; impacta `requirements.txt` y el task breakdown |
| **`DP-06`** — identificadores, timestamps, auditoría, borrado lógico | `INTEGER AUTOINCREMENT`, timestamps ISO en TEXT, sin columnas de auditoría, sin borrado lógico (cancelar conserva la fila = historial) | UUID, columnas `creado_en/modificado_en`, soft-delete | Cambios localizados en el esquema 001 + mapeo del repositorio; los specs no cambian |

Si el humano aprueba los valores provisorios, el plan se ejecuta tal cual; si aprueba con cambios, `design.md` y `tasks.md` se revisan **antes** de implementar.

## Risks / Trade-offs

- [`_sembrar()` de los tests accede a `self._turnos`] → único cambio de 1 línea aprobado en `tasks.md`; las 25 aserciones quedan intactas; `test_turnos.py` no se toca.
- [Deriva entre `ESTADOS_ACTIVOS` y el `IN` de SQL] → la cláusula se genera desde la constante de dominio + test "cancelado no bloquea vía BD".
- [Resolución de recursos por nombre podría ambiguar con nombres duplicados] → índice único provisorio `(tenant_id, nombre)`; revisar con `DP-06`/`PA-16`.
- [El default en memoria oculta errores del adaptador SQLite] → toda afirmación de persistencia se prueba solo con SQLite real (regla 5); el adaptador en memoria nunca se usa en tests de integración.
- [Concurrencia/`DP-05` no cubierta] → uso single-writer en tests; fuera de alcance, documentado.
- [Formato de fecha TEXT] → ISO-8601 y comparación lexicográfica = cronológica; revisar con `DP-06`/`DP-07`.
- [Solape de alcance `C-02`/`C-03` en `src/repositories/` e `src/infrastructure/`] → D1 fija el corte; confirmar con el usuario antes de aplicar.

## Migration Plan

1. Aprobación humana del design (gate CRITICO) → recién entonces tareas de código.
2. Infraestructura: esquema 001, config por entorno, seed (sin tocar el dominio) → suite actual en verde.
3. Puerto + adaptador en memoria + inyección en `ServicioTurnos` (+1 línea en `_sembrar`) → 25 tests verdes.
4. Adaptador SQLite + tests de integración → todos los escenarios de la capability nuevos en verde.
5. `pytest` + `pytest --cov=src` completos; commit Conventional (`feat:`/`test:`) **solo si el usuario lo pide**; rollback = revert del commit (los `.db` de dev son descartables y no se versionan).

## Open Questions

Preguntas que no alteran specs, enfoque ni desglose de tareas, y pueden responderse durante la implementación:

- Nombre exacto de la variable de entorno: propuesta `TURNO_DB_PATH` (alternativa `DATABASE_URL`).
- Soporte opcional de auto-carga de `.env` (requeriría sumar `python-dotenv`, única dependencia nueva posible).
- Columna `dni` de `paciente`: nullable ahora vs. UNIQUE provisorio (pendiente `PA-05`).
- Carpeta exacta de los tests de integración (`tests/` plano vs. `tests/integration/`, `architecture.md` §9 es "propuesta sujeta a validación").
