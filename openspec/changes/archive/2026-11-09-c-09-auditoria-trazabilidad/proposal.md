# Proposal

## Why

En un sistema odontológico multi-tenant (SaaS), la trazabilidad y la inmutabilidad de los eventos operativos y clínicos constituyen un requisito indispensable para la auditoría operativa, el cumplimiento normativo y la seguridad informática.

Actualmente, las acciones de negocio sobre turnos, recursos y pacientes se persisten en la base de datos (C-01 a C-08), pero no existe un registro histórico inmutable que capture de forma estandarizada qué usuario ejecutó cada operación, en qué momento exacto, sobre qué entidad y bajo qué parámetros.

El change `c-09-auditoria-trazabilidad` introduce la capacidad formal de **auditoría y trazabilidad** (`auditoria-trazabilidad`), proveyendo:
1. Una tabla relacional inmutable de eventos de auditoría (`auditoria`) acotada incondicionalmente a cada clínica (`tenant_id`).
2. La entidad de dominio pura `RegistroAuditoria` en `src/domain/models.py`.
3. El adaptador de persistencia `RepositorioAuditoriaSqlite`.
4. El endpoint protegido `GET /api/v1/auditoria` reservado exclusivamente para el rol `Administrador`, con filtros por rango de fechas, usuario, acción y entidad.
5. Control de acceso RBAC estricto, envelope uniforme de errores y pruebas con datos 100% sintéticos (RN-06).

## What Changes

- **Dominio Puro**:
  - Incorporación de la entidad `RegistroAuditoria` en `backend/src/domain/models.py` como `dataclass(frozen=True)` con campos `(id, tenant_id, usuario_id, accion, entidad, entidad_id, detalle, fecha_hora)`. Preserva 0 dependencias externas.
- **Persistencia Relacional y Migración 005**:
  - Nueva migración idempotente `backend/src/infrastructure/migrations/005_auditoria.sql` creando la tabla `auditoria` con claves foráneas hacia `tenant(id)` y `usuario(id)`, e índices compuestos `(tenant_id, fecha_hora)` y `(tenant_id, entidad, entidad_id)`.
  - Adaptador `RepositorioAuditoriaSqlite` en `backend/src/repositories/auditoria_sqlite.py` con métodos `registrar` y `listar` acotados incondicionalmente por `tenant_id`.
- **Capa API REST y Esquemas**:
  - Nuevos esquemas en `backend/src/api/esquemas.py`: `RegistroAuditoriaRespuesta`.
  - Router `backend/src/api/routers/auditoria.py` exponiendo `GET /api/v1/auditoria`.
  - Inyección de dependencias `obtener_repositorio_auditoria` en `backend/src/api/dependencias.py`.
  - Registro del router en `create_app()` de `backend/src/api/app.py`.
- **Seguridad y Control de Acceso RBAC**:
  - Requiere autenticación Bearer JWT.
  - Acceso restringido exclusivamente al rol `Administrador`. Otros roles (`Recepcionista`, `Profesional`) son denegados con HTTP 403 (`ACCESO_DENEGADO`).
  - Aislamiento horizontal estricto: Un administrador jamás puede visualizar registros de auditoría de otra clínica.
- **Envelope Uniforme de Errores**:
  - Errores de validación (422), acceso denegado (403) y falta de credenciales (401) bajo `{"error": {"code": "...", "message": "..."}}`.
- **Datos Sintéticos (RN-06)**:
  - Pruebas construidas con fixtures sintéticos sin PII real.

## Capabilities

### New Capabilities
- `auditoria-trazabilidad`: Registro y consulta de pistas de auditoría inmutables de operaciones clínicas y administrativas acotadas por tenant, restringidas al rol Administrador.

### Modified Capabilities
*(Ninguna. Las capacidades existentes conservan sus contratos intactos).*

## Impact

- **Persistencia**: Nueva migración `005_auditoria.sql` aplicada automáticamente por `migrar()`.
- **API**: Nuevo router `GET /api/v1/auditoria`.
- **Dependencias**: Inyección de `RepositorioAuditoriaSqlite`.
- **Tests**: Nueva suite `backend/tests/test_api_auditoria.py` con cobertura >= 97% y actualización de la prueba de migraciones `test_persistencia_esquema.py`.
