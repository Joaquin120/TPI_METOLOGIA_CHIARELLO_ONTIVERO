# Design

## Context

Ver `proposal.md — Why` para la motivación. El estado actual que condiciona el diseño:

- `backend/src/domain/services.py` — `ServicioTurnos` recibe `repositorio: PuertoTurnos | None = None` y, si es `None`, instancia `RepositorioTurnosEnMemoria` importado de `src.repositories.turnos_memoria`. Esa importación es la violación concreta de "dominio puro" que este change elimina. El servicio ya expone `agendar_turno()`, `turnos_registrados()`, `confirmar()`, `cancelar()` y `completar()`.
- `backend/src/domain/models.py` — entidades `frozen` con nombres (`Profesional.nombre`, `Sillon.nombre`, `Turno.paciente`) y `Turno.id` opcional; los estados son strings. No hay `tenant_id` en el dominio: la ventana de tenant vive en el repositorio (`RepositorioTurnosSqlite(conexion, tenant_id)`).
- `backend/src/infrastructure/` — `abrir_conexion(ruta)` (FKs + `sqlite3.Row`), `migrar(conexion)` (runner idempotente de `001_init.sql`), `ruta_base_de_datos()` (`TURNO_DB_PATH`), `sembrar_datos_iniciales(conexion)` (1 tenant, 2 profesionales, 2 sillones sintéticos).
- `backend/src/repositories/turnos_sqlite.py` — resuelve profesionales/sillones/pacientes **por nombre dentro del tenant** (upsert), filtra por `tenant_id`, aplica `[inicio, fin)` y `ESTADOS_ACTIVOS`.
- `backend/tests/` — 51 tests verdes contra SQLite real o repositorio en memoria; `test_turnos.py`, `test_estados_turno.py` y `test_persistencia_puerto.py` construyen `ServicioTurnos()` sin argumentos y deberán pasar a inyectar explícitamente el adaptador en memoria. `test_persistencia_puerto.py::test_servicio_usa_repositorio_en_memoria_por_defecto` afirma el default que este change elimina: se reemplaza por una aserción de `TypeError` (ver D2).
- Specs vigentes `crear-turno`, `gestionar-estados-turno` y `persistir-turnos` describen el comportamiento que la API **delega**, no reimplementa.
- Restricciones: reglas duras 1 (spec first), 2 (doble validación), 4 (suite verde), 5 (SQLite real, sin mocks), 6 (sin secretos), 7 (semiabierto), 8 (tenant siempre), 9 (Conventional Commits); `D-02`, `D-06`, `D-07`, `D-10`; `DP-01` se resuelve aquí.

## Goals / Non-Goals

**Goals:**

- Resolver `DP-01` con Python 3.11+ / FastAPI / Pydantic v2, sin ORM ni base de producción.
- Introducir `src/api/` con factoría de app, routers, esquemas y handlers; composición explícita `controlador → ServicioTurnos → RepositorioTurnosSqlite`.
- Eliminar todo acoplamiento del dominio hacia `src.repositories` y cualquier framework/DB, con un guard test automático.
- Exponer un slice vertical real (`health`, `POST /turnos`, `GET /turnos`) con contrato de error estable y tests `TestClient` contra SQLite real.
- Definir una resolución de tenant explícita, aislada en una dependencia reemplazable por `C-04`.

**Non-Goals:**

- Auth, RBAC, sesiones y tenant desde token (`C-04`).
- Filtros, paginación, `PATCH /turnos/{id}/estado`, endpoints de recursos/pacientes (`C-05`/`C-06`/`C-07`).
- Reprogramación (`C-08`), bloqueo de sillón (`C-10`), notificaciones (`C-14`).
- Base/ORM de producción (`DP-02`), estrategia física multi-tenant (`DP-03`), identificadores/auditoría definitivos (`DP-06`), concurrencia (`DP-05`).
- Cambiar el estado inicial del alta (`PA-13` sigue abierta: `CONFIRMADO`).
- Frontend (`C-11`+), CORS, despliegue (`DP-10`).

## Decisions

### D1 — Stack: FastAPI + Pydantic v2 (resuelve DP-01)

Se adopta **FastAPI** sobre Python 3.11+ con **Pydantic v2** para el contrato de entrada/salida.

- *Por qué*: el dominio ya es Python tipado; FastAPI deriva el esquema OpenAPI de los type hints, trae `TestClient` (basado en `httpx`) y permite inyección por dependencias sin framework propio.
- *Alternativas descartadas*: Flask (validación/serialización manual, sin OpenAPI nativo), Django REST Framework (arrastra ORM/`settings` y prejuzga `DP-02`), Node.js (descarta el núcleo Python ya implementado y `D-03`).
- `requirements.txt` sumará `fastapi`, `pydantic` y `httpx` (dependencia de `TestClient`). Versiones: últimas estables al aplicar, fijadas exactas tras instalar (consistente con el pinning actual de `pytest`). No se agrega ORM ni driver de producción.

### D2 — Desacople del dominio: repositorio obligatorio (BREAKING interno)

`ServicioTurnos.__init__` pasa a:

```python
def __init__(self, repositorio: PuertoTurnos) -> None:
    self._repositorio = repositorio
```

Se elimina el import `from src.repositories.turnos_memoria import RepositorioTurnosEnMemoria` y el default. El dominio solo conoce `PuertoTurnos` (`src/domain/puertos.py`).

- *Por qué*: un default que importa un adaptador concreto mantiene la dependencia dominio → persistencia aunque sea perezosa. El puerto ya existe; la inyección obligatoria hace explícita la dirección de dependencias y permite que el guard test sea estricto.
- *Impacto en call sites*: `test_turnos.py` y `test_estados_turno.py` pasan a `ServicioTurnos(RepositorioTurnosEnMemoria())`; los tests de persistencia ya inyectan SQLite. No cambia ningún escenario ni aserción. El helper `_sembrar()` sigue usando `servicio._repositorio.agregar(...)`.
- *Excepción obligatoria*: `test_persistencia_puerto.py::test_servicio_usa_repositorio_en_memoria_por_defecto` no puede "ajustarse": verifica el comportamiento que el change elimina. Se reemplaza por `test_servicio_exige_repositorio`, que exige `TypeError` al construir sin argumento; el resto del archivo solo cambia la construcción. Sin esta sustitución la suite quedaría roja (regla dura 4).
- *Alternativa descartada*: mover `RepositorioTurnosEnMemoria` a `src/domain/` — mete persistencia (aunque sea en memoria) en el dominio y contradice `architecture.md` §3.
- *Alternativa descartada*: import perezoso dentro de `__init__` — sigue siendo acoplamiento y el guard lo detectaría.

### D3 — Factoría de app, conexión por petición y composición explícita

Nuevo paquete:

```text
backend/src/api/
├── __init__.py
├── app.py            # create_app(): factoría y wiring
├── dependencias.py   # contexto de petición: conexión, tenant, servicio
├── errores.py        # envelope + handlers de excepción
├── esquemas.py       # Pydantic: TurnoCrear, TurnoRespuesta, ErrorRespuesta
└── routers/
    ├── __init__.py
    ├── health.py
    └── turnos.py
```

`create_app(*, ruta_db: str | Path | None = None, tenant_por_defecto: int | None = None, sembrar: bool = False) -> FastAPI`:

1. Resuelve `ruta_db` (parámetro o `ruta_base_de_datos()`).
2. Abre una conexión, ejecuta `migrar()` y, si `sembrar=True`, `sembrar_datos_iniciales()`; cierra la conexión.
3. Guarda `ruta_db` y `tenant_por_defecto` en `app.state` (no hay estado global de módulo).
4. Registra handlers de excepción e incluye los routers bajo `/api/v1`.
5. Devuelve la app.

No existe un `app = create_app()` a nivel de módulo. Uvicorn se ejecuta con `uvicorn src.api.app:create_app --factory`.

Cada petición de negocio abre su propia conexión SQLite mediante una dependencia con `yield` y la cierra al terminar:

```python
@dataclass(frozen=True)
class ContextoTurnos:
    servicio: ServicioTurnos
    tenant_id: int

def contexto_turnos(request: Request, x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID")) -> Iterator[ContextoTurnos]:
    conexion = abrir_conexion(request.app.state.ruta_db)
    try:
        tenant_id = _resolver_tenant(conexion, x_tenant_id, request.app.state.tenant_por_defecto)
        servicio = ServicioTurnos(RepositorioTurnosSqlite(conexion, tenant_id=tenant_id))
        yield ContextoTurnos(servicio=servicio, tenant_id=tenant_id)
    finally:
        conexion.close()
```

- *Por qué conexión por petición*: evita compartir una conexión `sqlite3` entre hilos (FastAPI ejecuta endpoints sync en un threadpool) y elimina el riesgo de `check_same_thread`. El costo es despreciable para SQLite local.
- *Alternativa descartada*: conexión única en `app.state` — requiere `check_same_thread=False` y un locking manual; prematuro y riesgoso.
- *Alternativa descartada*: dependencia global de base — oculta el wiring y dificulta tests con `tmp_path`.

### D4 — Resolución de tenant provisoria y reemplazable

Orden de precedencia:

1. Encabezado `X-Tenant-ID` (entero).
2. `tenant_por_defecto` del `create_app(...)`.
3. Variable de entorno `TURNO_TENANT_ID` leída en la factoría (nunca hardcodeada; `D-05`).
4. Si no hay tenant → `400` `TENANT_NO_RESUELTO`.

El tenant se valida contra la tabla `tenant` (`SELECT 1 FROM tenant WHERE id = ?`); un id inexistente también produce `400` y nunca se consulta con un tenant fantasma. El `tenant_id` se inyecta en `RepositorioTurnosSqlite` y **nunca** se acepta en el cuerpo (`extra="forbid"`).

- *Por qué*: `C-04` todavía no existe y el tenant no puede omitirse (regla dura 8). Una única dependencia (`_resolver_tenant`) concentra el seam que `C-04` reemplazará por claims de sesión/JWT.
- *Riesgo asumido*: el header es falsificable. Se documenta como **temporal, solo desarrollo/pruebas**; no es un mecanismo de seguridad.
- *Alternativa descartada*: tenant fijo `1` en código — viola "tenant siempre presente" y no permite probar aislamiento.

### D5 — Contrato API alineado al dominio actual (nombres, no ids)

El contrato usa **nombres** porque el dominio y `RepositorioTurnosSqlite` resuelven recursos por nombre dentro del tenant. No se inventan `paciente_id`/`profesional_id`/`sillon_id` que el dominio aún no acepta.

**`GET /api/v1/health`** → `200`

```json
{ "status": "ok" }
```

**`POST /api/v1/turnos`** → `201`; request:

```json
{
  "paciente": "Paciente Ficticio",
  "profesional": "Dr. Ejemplo",
  "sillon": "Sillón 1",
  "fecha": "2026-11-01",
  "hora_inicio": "10:00",
  "hora_fin": "10:30"
}
```

Response (mismo shape que el ítem del listado):

```json
{
  "id": 1,
  "paciente": "Paciente Ficticio",
  "profesional": "Dr. Ejemplo",
  "sillon": "Sillón 1",
  "fecha": "2026-11-01",
  "hora_inicio": "10:00",
  "hora_fin": "10:30",
  "estado": "CONFIRMADO"
}
```

**`GET /api/v1/turnos`** → `200` con un array de objetos con el mismo shape. Sin filtros ni paginación en este change.

Validación Pydantic: campos no vacíos; `fecha` con patrón `YYYY-MM-DD`; horas con patrón `HH:MM` 24 h; `extra="forbid"`. No se valida `hora_inicio < hora_fin` porque pertenece a `RP-01` (abierta) y no se resuelve aquí.

- *Contrato futuro*: cuando `C-05`/`C-06` expongan recursos y `DP-06` fije identificadores, se migrará a `*_id` con una versión de API o transición documentada. Se registra como deuda explícita, no como omisión.
- *Nota*: el repositorio hace upsert de recursos por nombre; un nombre desconocido se crea. La validación de existencia de recursos pertenece a `C-05`/`C-06`.

### D6 — Envelope de error estable y mapeo de excepciones

Forma única:

```json
{ "error": { "code": "SOLAPAMIENTO_PROFESIONAL", "message": "El profesional Dr. Ejemplo ya tiene un turno ..." } }
```

| Origen | HTTP | `error.code` |
|---|---|---|
| `SolapamientoProfesionalError` | `409` | `SOLAPAMIENTO_PROFESIONAL` |
| `SolapamientoSillonError` | `409` | `SOLAPAMIENTO_SILLON` |
| `TransicionInvalidaError` | `409` | `TRANSICION_INVALIDA` |
| `RequestValidationError` (Pydantic/FastAPI) | `422` | `VALIDACION` |
| `ErrorTenantNoResuelto` (excepción de la capa API) | `400` | `TENANT_NO_RESUELTO` |

Los handlers viven en `src/api/errores.py` y se registran en `create_app`. `TransicionInvalidaError` se mapea aunque el endpoint de cambio de estado sea de `C-05`; se verifica con una ruta exclusiva de test montada sobre la app (nunca en producción).

- *Por qué*: `features.md` §5.2 deja los códigos HTTP pendientes; este change los define y los convierte en contrato verificable.
- *Alternativa descartada*: dejar que FastAPI serialice las excepciones por defecto — el cliente recibiría shapes distintos (`detail` vs. texto) y no habría `code` estable.

### D7 — Pureza del dominio verificada por guard test

`backend/tests/test_pureza_dominio.py` recorre `backend/src/domain/*.py`, parsea cada archivo con `ast` y recolecta módulos de `Import`/`ImportFrom`. Falla si aparece cualquier prefijo prohibido:

- `fastapi`, `pydantic`, `starlette`, `httpx`
- `sqlite3`, `sqlalchemy`, `alembic`
- `src.repositories`, `src.infrastructure`, `src.api`

Además verifica que `src/domain/services.py` ya no importe `src.repositories.turnos_memoria`. El test es la red de seguridad permanente de la regla "cero acoplamiento en el dominio".

### D8 — Estrategia de pruebas (reglas duras 4 y 5)

- **Unitarias existentes**: se mantienen contra `RepositorioTurnosEnMemoria`, ahora inyectado explícitamente; sin BD ni HTTP. Solo cambia la construcción, no escenarios ni aserciones.
- **API con `TestClient`** (`backend/tests/test_api_turnos.py`): SQLite **real** en archivo temporal (`tmp_path`), migrado y sembrado. Se usa archivo (no `:memory:`) porque cada petición abre su propia conexión y una base `:memory:` no se comparte entre conexiones. Nunca se mockea la base.
- Casos: health; alta feliz + persistencia vía GET; conflicto de profesional 409; conflicto de sillón 409; validación 422 (campo faltante y hora inválida); listado aislado por tenant; tenant ausente 400; envelope de error; mapeo de transición inválida vía ruta de test; guard de pureza.
- Cierre obligatorio: `cd backend && pytest` 100 % verde y `pytest --cov=src` sin regresión.

### D9 — Plan TDD (Strict TDD)

Cada task de `tasks.md` sigue RED → GREEN → TRIANGULATE (≥2 casos) → REFACTOR → red de seguridad (suite completa). Orden: dependencias → desacople del dominio (con tests existentes verdes) → guard de pureza → factoría/DI → esquemas → handlers → health → POST/GET → suite completa. No se escribe código de producción sin el test que falla primero.

## Risks / Trade-offs

- [El header `X-Tenant-ID` es falsificable] → se documenta como provisorio; `C-04` lo reemplaza por claims de sesión. No se usa en producción.
- [Contrato por nombres difiere del ejemplo `*_id` de `features.md` §5.1] → se elige lo que el dominio puede hacer hoy y se registra la migración futura; no se inventan ids.
- [El repositorio crea recursos por nombre (upsert)] → un typo puede crear un profesional/sillón nuevo; la validación de recursos llega con `C-05`/`C-06`. Se documenta en el contrato.
- [Conexión por petición en SQLite] → overhead mínimo y sin problemas de hilos; si el volumen crece, `DP-02`/`DP-05` definirán pool/transacciones.
- [Cambio de constructor de `ServicioTurnos` toca tests existentes] → solo líneas de construcción; los escenarios y aserciones quedan intactos y la suite completa es la red de seguridad.
- [FastAPI/Pydantic agregan superficie de dependencias] → versiones fijadas tras instalar; sin ORM ni servicios externos.
- [`PA-13` abierta] → el alta sigue naciendo `CONFIRMADO`; la API no decide el estado inicial.
- [`RP-01` abierta] → la API valida formato, no coherencia `inicio < fin`; se documenta como deuda.
- [Handler de `TransicionInvalidaError` sin endpoint productivo] → se prueba con una ruta de test; el contrato queda listo para `C-05`.

## Migration Plan

1. Aprobar este design (incluye el cambio de constructor de `ServicioTurnos`).
2. Agregar dependencias y fijarlas; suite actual verde antes de tocar código.
3. Desacoplar el dominio (repositorio obligatorio) y ajustar construcciones en tests; suite verde.
4. Agregar guard de pureza (debe fallar antes del desacople si se escribe primero; orden TDD en `tasks.md`).
5. Crear `src/api/` (esquemas, errores, dependencias, routers, factoría) con tests `TestClient`.
6. Ejecutar suite completa y cobertura; commit Conventional (`feat:`/`test:`) solo si el usuario lo pide.
7. Rollback: revertir el commit; no hay migraciones nuevas ni datos productivos. La base SQLite de desarrollo es descartable.

## Open Questions

- **`DP-02`** — base/ORM de producción: sin cambios; SQLite sigue siendo dev/test.
- **`DP-03`** — estrategia física de aislamiento multi-tenant: sin cambios; se mantiene `tenant_id` en repositorios.
- **`DP-04`** — auth/sesiones: `C-04` reemplazará `X-Tenant-ID`/`TURNO_TENANT_ID` por el tenant de la sesión. El seam ya está aislado.
- **`PA-13`** — estado inicial del alta: se conserva `CONFIRMADO`; la API no lo altera.
- **`DP-06`** — identificadores definitivos: el contrato por nombres se revisará cuando se adopten `*_id`.

## UI Mockups

- **Decision: no (no UI)** — 2026-11-04.
- Justificación: change exclusivamente backend (capa HTTP/JSON). No crea ni modifica pantallas, componentes, layouts, estilos ni interacciones. No hay `design-system/` aprobado y este change no lo requiere. No se ejecuta el gate de mockups.
