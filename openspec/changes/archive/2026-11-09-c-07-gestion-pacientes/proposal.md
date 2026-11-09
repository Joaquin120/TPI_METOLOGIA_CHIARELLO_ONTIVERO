# Proposal

## Why

Para registrar y asociar turnos odontológicos a personas reales en el flujo clínico (F-01, F-11), el personal de recepción y administración necesita un catálogo de pacientes propio de su centro odontológico (tenant). Hasta el momento, el modelo `Turno` registra al paciente como una cadena de texto plana o como referencia provisoria en `paciente` (001_init.sql), sin validación de identidad (DNI de 8 dígitos), sin datos de contacto (teléfono para futuras notificaciones WhatsApp, C-14) y sin endpoints REST para su alta y consulta filtrada.

Este cambio introduce la capacidad `gestionar-pacientes` (Change C-07), definiendo el contrato HTTP formal (`POST /api/v1/pacientes`, `GET /api/v1/pacientes`), la evolución del esquema relacional en SQLite con aislamiento multi-tenant estricto y unicidad de DNI por clínica, y la adopción de la skill `.atl/skills/generador-datos-pacientes-sinteticos.md` para garantizar privacidad absoluta (RN-06, regla dura 3) con cobertura >= 97%.

## What Changes

- **Evolución del esquema relacional en SQLite**:
  - Nueva migración idempotente `004_pacientes.sql` que añade la columna `telefono TEXT` a la tabla `paciente`, formaliza `dni TEXT NOT NULL` y establece un índice de unicidad compuesto `UNIQUE(tenant_id, dni)` (permitiendo que dos clínicas distintas atiendan al mismo paciente con idéntico DNI, pero impidiendo duplicados dentro de la misma clínica).
- **Modelo de Dominio Puro**:
  - Extensión de la entidad `Paciente` en `backend/src/domain/models.py` como `dataclass(frozen=True)` con campos `dni: str`, `nombre: str`, `telefono: str`, `tenant_id: int` e `id: int | None = None`, sin acoplamiento a frameworks (0 imports prohibidos, testeado por `test_pureza_dominio.py`).
- **Persistencia y Repositorio Multi-Tenant**:
  - Creación de `RepositorioPacientesSqlite` en `backend/src/repositories/pacientes_sqlite.py` con métodos `crear(paciente)`, `buscar_por_id(id, tenant_id)`, `buscar_por_dni(dni, tenant_id)` y `listar(tenant_id, filtro_nombre=None, filtro_dni=None)` con aislamiento estricto por `tenant_id`.
- **Capa API REST y Envelope Uniforme de Errores**:
  - Nuevos esquemas Pydantic en `backend/src/api/esquemas.py`: `PacienteCrear` (con validación regex para DNI de 8 dígitos `^\d{8}$`, teléfono válido y `extra="forbid"`) y `PacienteRespuesta` (incluyendo `id`, `tenant_id`, `dni`, `nombre`, `telefono`).
  - Nuevo router `backend/src/api/routers/pacientes.py` exponiendo:
    - `POST /api/v1/pacientes`: Alta de paciente (código 201). Rechaza duplicados en el mismo tenant con código 409 (`PACIENTE_DUPLICADO`) y errores de validación con código 422 (`VALIDACION`).
    - `GET /api/v1/pacientes`: Listado acotado al tenant del usuario autenticado, con soporte para query params `dni` y `nombre`.
  - Respuestas de error estandarizadas con el envelope `{"error": {"code": "...", "message": "..."}}`.
- **Control de Acceso y RBAC**:
  - Requiere autenticación JWT Bearer válida (401 ante token faltante o inválido).
  - Resolución del permiso pendiente de `actors.md` §7: Alta de pacientes permitida para roles `Recepcionista` y `Administrador`. Consulta permitida para `Recepcionista`, `Administrador` y `Profesional`.
- **Fixtures Sintéticos y Auditoría de Privacidad (RN-06)**:
  - Generación de fixtures de prueba determinísticos y 100% ficticios guiados por `.atl/skills/generador-datos-pacientes-sinteticos.md` en `backend/tests/test_api_pacientes.py`.

## Capabilities

### New Capabilities
- `gestionar-pacientes`: Alta, consulta y validación de pacientes dentro del tenant autenticado, garantizando datos sintéticos (RN-06), unicidad de DNI por tenant, validación de formato de documento y teléfono, y envelope uniforme de errores.

### Modified Capabilities
*(Ninguna. Las capacidades existentes `consultar-recursos`, `exponer-api-turnos`, `crear-turno`, `persistir-turnos`, `gestionar-estados-turno` y `autenticacion-autorizacion` conservan sus requisitos normativos).*

## Impact

- **Base de datos**: Nueva migración `backend/src/infrastructure/migrations/004_pacientes.sql`.
- **Dominio**: Actualización de la entidad `Paciente` en `backend/src/domain/models.py`.
- **Persistencia**: Implementación de `backend/src/repositories/pacientes_sqlite.py`.
- **Capa API**:
  - Nuevos esquemas en `backend/src/api/esquemas.py`.
  - Nuevo router en `backend/src/api/routers/pacientes.py` registrado en `backend/src/api/app.py`.
  - Manejo de excepciones de conflicto en `backend/src/api/errores.py` (`ErrorPacienteDuplicado` -> 409).
- **Semilla**: Inclusión de pacientes sintéticos de ejemplo en `backend/src/infrastructure/seed.py`.
- **Tests**: Nueva suite de integración `backend/tests/test_api_pacientes.py` con cobertura >= 97%.
