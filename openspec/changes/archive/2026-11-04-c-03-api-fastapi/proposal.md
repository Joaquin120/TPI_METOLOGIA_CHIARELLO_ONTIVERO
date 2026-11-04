# Proposal

> **Trazabilidad de nombre**: `c-03-api-fastapi` ≡ roadmap **C-03 `capa-api-desacoplada`** (`CHANGES.md`, FASE 0, GATE 2). El nombre del change refleja la resolución de `DP-01`; el alcance es el del roadmap.

## Why

El dominio ya valida la doble disponibilidad y persiste turnos en SQLite, pero no existe una capa de presentación: recepción no puede operar la agenda por HTTP y el dominio todavía importa `RepositorioTurnosEnMemoria` desde `src.repositories`, lo que viola el principio de **dominio puro** (`architecture.md` §1 y §3). C-03 cierra el "desacople de backend" exponiendo un contrato REST estable sin arrastrar HTTP ni persistencia hacia el dominio, y desbloquea `C-04` (auth/RBAC/tenancy) y `C-05` (endpoints completos de turnos).

## What Changes

Los cinco pilares de este change, en orden de dependencia:

1. **Stack: API REST con FastAPI (resuelve `DP-01`)** — Python 3.11+ con **FastAPI** y **Pydantic v2**, sin ORM ni base de producción. SQLite continúa como base de desarrollo y pruebas (`D-04`); `DP-02` permanece abierto y no se decide aquí.
2. **Esquemas Pydantic de entrada/salida** — modelos `TurnoCrear` (campos no vacíos, `fecha` `YYYY-MM-DD`, horas `HH:MM` 24 h, `extra="forbid"` para que el cliente no pueda inyectar `tenant_id`) y `TurnoRespuesta` (mapeo 1:1 desde `Turno`, reutilizado por alta y listado), más el envelope de error.
3. **Inyección del repositorio SQLite (composition root)** — la factoría `create_app(*, ruta_db=None, tenant_por_defecto=None, sembrar=False)` ensambla `router → ServicioTurnos → RepositorioTurnosSqlite` con la conexión y el `tenant_id` inyectados por petición; no hay conexiones ni `app` global a nivel de módulo. Arranque vía `uvicorn src.api.app:create_app --factory`.
4. **Cero acoplamiento en el dominio** — `ServicioTurnos` deja de importar `src.repositories.turnos_memoria` y recibe el repositorio como **argumento obligatorio** del constructor (`PuertoTurnos`). Es **BREAKING interno, no de contrato HTTP**: se ajustan solo las construcciones en tests existentes, sin tocar escenarios ni aserciones. Un **guard test** verifica automáticamente que `src/domain/` no importe `fastapi`, `pydantic`, `sqlite3`, `src.repositories` ni `src.infrastructure`.
5. **Tests de endpoints con `TestClient`** — `fastapi.testclient.TestClient` contra **SQLite real** en archivo temporal, migrado y sembrado, nunca mockeado (regla dura 5): health, alta feliz, persistencia verificada por listado, conflictos de profesional y sillón, validación 422, aislamiento por tenant, tenant ausente y mapeo de transición inválida.

**Endpoints del slice vertical** (bajo `/api/v1`):

- `GET /health` — health check, sin tenant.
- `POST /turnos` — alta de turno; la doble validación (profesional y sillón) se delega íntegramente al dominio.
- `GET /turnos` — listado de turnos del tenant resuelto; sin filtros ni paginación en este change.

**Contrato de errores JSON estable**: `{"error": {"code": "...", "message": "..."}}`, con excepciones de dominio mapeadas a `409` (`SOLAPAMIENTO_PROFESIONAL`, `SOLAPAMIENTO_SILLON`, `TRANSICION_INVALIDA`) y validación de entrada a `422 VALIDACION`.

**Fuera de alcance** (changes posteriores): auth/RBAC y tenant desde sesión (`C-04`); filtros `profesional_id`/`sillon_id`/`fecha`, `PATCH /turnos/{id}/estado`, endpoints de recursos y pacientes (`C-05`/`C-06`/`C-07`); reprogramación (`C-08`); base/ORM de producción (`DP-02`); frontend (`C-11`+). No se resuelve `PA-13` (estado inicial del alta sigue `CONFIRMADO`).

## Capabilities

### New Capabilities

- `exponer-api-turnos`: contrato HTTP/JSON para health, alta y listado de turnos; mapeo estable de errores de dominio a códigos HTTP; resolución provisoria y reemplazable de tenant; y garantía verificable de que el dominio permanece libre de HTTP y persistencia.

### Modified Capabilities

Ninguna. `crear-turno`, `gestionar-estados-turno` y `persistir-turnos` conservan su comportamiento observable: la API **delega** en el dominio y no reimplementa reglas. La eliminación del default en memoria de `ServicioTurnos` es un detalle de implementación, no un cambio de spec.

## Impact

- **Código afectado**: `backend/src/api/` (nuevo), `backend/src/domain/services.py` (desacople de persistencia), `backend/tests/` (nuevos tests de API + ajuste de construcción en tres archivos existentes, incluida la sustitución del test que afirmaba el repositorio por defecto), `backend/requirements.txt`.
- **API**: se introducen `/api/v1/health`, `POST /api/v1/turnos` y `GET /api/v1/turnos`. El contrato definitivo de filtros y cambios de estado queda para `C-05`.
- **Dependencias**: `fastapi`, `pydantic` y `httpx` (requerido por `fastapi.testclient.TestClient`). No se agrega ORM ni driver de producción.
- **Sistemas**: SQLite local (dev/test) sin cambios de esquema; migración 001 y seed reutilizados.
- **Riesgos**: resolución de tenant provisoria por header/config hasta `C-04`; `DP-02`/`DP-03`/`DP-04`/`PA-13` siguen abiertos y se documentan como tales.
