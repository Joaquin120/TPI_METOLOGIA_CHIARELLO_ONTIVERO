# Proposal

## Why
Actualmente la API expone únicamente la creación básica de turnos (`POST /api/v1/turnos`) y un listado sin filtros (`GET /api/v1/turnos`), sin capacidad de consultar la agenda por fecha, profesional o sillón, ni de restringir la visión del profesional a su propia agenda, ni de gestionar el ciclo de vida del turno (`RN-03`, `RN-04`) vía HTTP. Este change completa la superficie REST del módulo Agenda del MVP (`F-01`, `F-02`, `F-03`), permitiendo operar los turnos con filtros dinámicos, control de acceso por rol y transiciones de estado que liberan recursos inmediatamente al cancelar.

## What Changes
- **Filtros en consulta de turnos (`GET /api/v1/turnos`)**: Incorporación de parámetros de consulta opcionales `fecha` (formato `YYYY-MM-DD`), `profesional_id` (entero) y `sillon_id` (entero), manteniendo el aislamiento estricto por tenant (`RN-05`).
- **Restricción de agenda por rol Profesional**: Si el usuario autenticado posee el rol `Profesional`, el listado solo devuelve los turnos asignados a su propio `profesional_id`, ignorando o denegando cualquier intento de consultar turnos de otros profesionales (`knowledge-base/actors.md` §3).
- **Transición de estados de turnos (`PATCH /api/v1/turnos/{id}/estado`)**: Endpoint protegido para aplicar transiciones del ciclo de vida (`confirmar`, `cancelar`, `completar`) según `RN-03`. Si la acción es `cancelar`, los recursos asignados (profesional y sillón) quedan inmediatamente liberados para nuevos agendamientos en ese intervalo (`RN-04`).
- **Control de acceso y excepciones HTTP**:
  - `POST` y `PATCH` restringidos a roles autorizados (`Recepcionista`, `Administrador`).
  - Mapeo de turno inexistente en el tenant a `404` (`{"error": {"code": "TURNO_NO_ENCONTRADO", "message": "..."}}`).
  - Mapeo de transiciones inválidas a `409` (`{"error": {"code": "TRANSICION_INVALIDA", "message": "..."}}`).
  - Mapeo de datos o parámetros inválidos a `422` (`{"error": {"code": "VALIDACION", "message": "..."}}`).

## Capabilities

### New Capabilities

### Modified Capabilities
- `exponer-api-turnos`: Se amplía el requisito de listado de turnos para incorporar filtros opcionales (`fecha`, `profesional_id`, `sillon_id`) y restricción de visibilidad para el rol `Profesional`; se añade el requisito de cambio de estado de turno vía HTTP (`PATCH /api/v1/turnos/{id}/estado`) con liberación inmediata de recursos en cancelación y códigos de error normalizados (404, 409, 422).

## Impact
- **Rutas y API (`src/api/routers/turnos.py`)**: Nuevos query params en `GET /turnos` y nuevo endpoint `PATCH /turnos/{id}/estado`.
- **Esquemas Pydantic (`src/api/esquemas.py`)**: Nuevos esquemas para filtros de búsqueda y cuerpo de solicitud de cambio de estado (`TurnoCambioEstado`).
- **Adaptador de persistencia (`src/repositories/turnos_sqlite.py`)**: Soporte de filtros combinables en `listar(...)` y método para recuperar turno individual por id y tenant.
- **Servicio y puertos (`src/domain/`)**: Integración en `PuertoTurnos` y `ServicioTurnos` de búsqueda por ID y filtros opcionales preservando la pureza de dominio.
- **Suite de pruebas**: Nuevos tests de integración y contrato en `backend/tests/` verificando caminos felices, combinaciones de filtros, control RBAC, transiciones inválidas, 404, y liberación de recursos en re-agendamiento.

