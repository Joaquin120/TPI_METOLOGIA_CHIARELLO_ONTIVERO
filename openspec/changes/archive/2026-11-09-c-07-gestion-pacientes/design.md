# Design

## Context

El sistema cuenta con persistencia en SQLite, arquitectura desacoplada, autenticación JWT con control de roles y catálogo de recursos clínicos acotado al tenant (C-01 a C-06). En la migración inicial `001_init.sql`, la tabla `paciente` se definió de forma provisoria con columnas `(id, tenant_id, nombre, dni)` donde `dni` era nullable, carecía de columna `telefono` y la unicidad estaba ligada únicamente al nombre (`UNIQUE(tenant_id, nombre)`), dejando abierta la formalización del alta de pacientes (PA-05).

Ver `proposal.md` para la justificación y motivación de este cambio. Para los requisitos normativos y escenarios de prueba, consultar `specs/gestionar-pacientes/spec.md`.

## Goals / Non-Goals

**Goals:**
- Exponer los endpoints REST `POST /api/v1/pacientes` y `GET /api/v1/pacientes` protegidos por autenticación Bearer JWT y control de roles RBAC.
- Evolucionar el esquema relacional mediante una nueva migración idempotente `004_pacientes.sql` incorporando la columna `telefono TEXT` y la restricción de unicidad compuesta `UNIQUE(tenant_id, dni)`.
- Extender la entidad de dominio `Paciente` en `backend/src/domain/models.py` preservando la pureza arquitectónica (cero dependencias de frameworks o drivers).
- Implementar el adaptador de persistencia `RepositorioPacientesSqlite` con aislamiento estricto por `tenant_id`.
- Garantizar el envelope uniforme de errores `{"error": {"code": "...", "message": "..."}}` ante validaciones (422), duplicados (409), autenticación (401) y permisos (403).
- Implementar la suite de pruebas `backend/tests/test_api_pacientes.py` bajo las pautas de `.atl/skills/generador-datos-pacientes-sinteticos.md` garantizando RN-06 y cobertura >= 97%.

**Non-Goals:**
- Modificación o baja lógica de pacientes (CRUD completo de pacientes diferido para evolutivos posteriores).
- Portal o autoservicio del paciente (PA-05 abierta fuera del MVP).
- Módulo de historia clínica o ficha odontológica detallada.

## Decisions

### D1: Migración incremental `004_pacientes.sql` y unicidad de DNI
- **Decisión**: Crear `backend/src/infrastructure/migrations/004_pacientes.sql` para añadir la columna `telefono TEXT` y crear el índice de unicidad `CREATE UNIQUE INDEX IF NOT EXISTS idx_paciente_tenant_dni ON paciente (tenant_id, dni)`.
- **Razón**: Permite la evolución no destructiva de bases de datos existentes sin modificar los scripts previos (`001_init.sql` a `003_recursos.sql`), respetando la inmutabilidad de migraciones aplicadas.
- **Alternativa descartada**: Recrear la base o alterar `001_init.sql`, lo cual rompería la trazabilidad de bases de datos existentes.

### D2: Unicidad compuesta multi-tenant `(tenant_id, dni)`
- **Decisión**: La unicidad de DNI se aplica exclusivamente a nivel de clínica (`tenant_id`).
  - Si una persona física se atiende en dos clínicas distintas (`tenant_id = 1` y `tenant_id = 2`), se admiten registros independientes con el mismo DNI en ambas (201 Created).
  - Si se intenta duplicar el DNI en la misma clínica (`tenant_id = 1`), la operación se rechaza con código HTTP 409 y código `PACIENTE_DUPLICADO`.
- **Razón**: En un SaaS odontológico multi-tenant, cada clínica es legal y operativamente independiente. Forzar unicidad global de DNI violaría el aislamiento y filtraría información sobre la concurrencia de pacientes a otros centros.
- **Alternativa descartada**: Unicidad global de DNI en toda la tabla.

### D3: Pureza del modelo de dominio `Paciente`
- **Decisión**: Modelar la entidad `Paciente` en `backend/src/domain/models.py` como `dataclass(frozen=True)` con campos `dni: str`, `nombre: str`, `telefono: str`, `tenant_id: int` e `id: int | None = None`.
- **Razón**: El dominio no debe depender de librerías web (`fastapi`, `pydantic`) ni de bases de datos (`sqlite3`). Esto asegura conformidad con las reglas de arquitectura y pasa los guard tests de `backend/tests/test_pureza_dominio.py`.
- **Alternativa descartada**: Usar modelos de Pydantic o tablas ORM dentro de `src/domain/`.

### D4: Esquemas de validación y control de atributos (`extra="forbid"`)
- **Decisión**: En `src/api/esquemas.py`, `PacienteCrear` valida:
  - `dni`: Regex `^\d{8}$` (exactamente 8 dígitos numéricos).
  - `nombre`: String no vacío con `strip_whitespace=True`.
  - `telefono`: String no vacío con formato de teléfono válido.
  - `model_config = ConfigDict(extra="forbid")`: Prohíbe inyectar `tenant_id` o `id` desde el cuerpo. El `tenant_id` se resuelve siempre desde el token JWT del usuario autenticado.
- **Razón**: Evita ataques de suplantación de tenant (Regla Dura 8: *Tenant siempre presente*).
- **Alternativa descartada**: Permitir que el cliente especifique `tenant_id` en el JSON de entrada.

### D5: Resolución de permisos RBAC para pacientes
- **Decisión**: Resolver la pregunta abierta de `actors.md` §7:
  - `POST /api/v1/pacientes`: Autorizado para roles `Recepcionista` y `Administrador`.
  - `GET /api/v1/pacientes`: Autorizado para roles `Recepcionista`, `Administrador` y `Profesional` (para consultar contacto de sus pacientes asignados).
- **Razón**: La recepción y administración coordinan el padrón de pacientes y su contacto; los profesionales necesitan consultar información básica de sus pacientes pero no gestionan el alta administrativa en el MVP.
- **Alternativa descartada**: Permitir alta de pacientes a cualquier rol sin distinción.

### D6: Adopción obligatoria de la skill `generador-datos-pacientes-sinteticos`
- **Decisión**: Los fixtures de prueba y validaciones de `test_api_pacientes.py` deben construirse siguiendo los patrones sintéticos de `.atl/skills/generador-datos-pacientes-sinteticos.md`.
- **Razón**: Asegura el cumplimiento de RN-06 (privacidad estricta, regla dura 3), evitando el uso de PII real en fixtures y garantizando una cobertura de código >= 97%.

## Risks / Trade-offs

- **[Riesgo: Colisión de nombres en pacientes con mismo DNI en distintos tenants]** → *Mitigación:* Se añade el índice compuesto `(tenant_id, dni)` y el índice provisorio de nombre se mantiene o relaja sin comprometer la integridad.
- **[Riesgo: Filtración de pacientes entre clínicas en búsquedas]** → *Mitigación:* El repositorio añade incondicionalmente la cláusula `WHERE tenant_id = :tenant_id` tanto en listados completos como en filtros por DNI o nombre.

## Migration Plan

1. Ejecución del script `004_pacientes.sql` mediante `migrar(conexion)` al iniciar la aplicación o las pruebas.
2. La migración es idempotente y se registra en la tabla `schema_migrations`.
