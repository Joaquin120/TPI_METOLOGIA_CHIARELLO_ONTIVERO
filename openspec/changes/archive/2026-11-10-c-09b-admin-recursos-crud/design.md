# Design

## Context

El sistema cuenta con lectura de recursos clínicos (profesionales y sillones) implementada en C-06 (`backend/src/repositories/recursos.py` y `backend/src/api/routers/recursos.py`). La estructura relacional definida en las migraciones `001_init.sql` y `003_recursos.sql` ya contiene las columnas operativas `matricula`, `especialidad`, `equipamiento` y `activo`, así como las restricciones de unicidad `UNIQUE(tenant_id, nombre)` en ambas tablas.

Sin embargo, las operaciones de escritura (altas y modificaciones administrativas) no están expuestas en la API REST y los repositorios solo proveen `resolver_id`, `obtener_por_id` y `listar`.

Consultar `proposal.md` para la motivación general del cambio y `specs/administrar-recursos/spec.md` para los requisitos normativos y escenarios Given/When/Then.

## Goals / Non-Goals

**Goals:**
- Exponer endpoints REST en `backend/src/api/routers/recursos.py`:
  - `POST /api/v1/profesionales` (201 Created)
  - `PUT /api/v1/profesionales/{id}` (200 OK)
  - `POST /api/v1/sillones` (201 Created)
  - `PUT /api/v1/sillones/{id}` (200 OK)
- Implementar los métodos de persistencia `crear` y `actualizar` en `RepositorioProfesionales` y `RepositorioSillones`.
- Restringir el acceso estrictamente al rol `Administrador` mediante RBAC (`requerir_rol("Administrador")`).
- Manejar conflictos de duplicidad de nombres en el mismo tenant devolviendo HTTP 409 con código `NOMBRE_PROFESIONAL_DUPLICADO` o `NOMBRE_SILLON_DUPLICADO`.
- Devolver HTTP 404 (`PROFESIONAL_NO_ENCONTRADO` / `SILLON_NO_ENCONTRADO`) si el recurso no existe o pertenece a otro tenant.
- Registrar eventos de auditoría inmutables (`CREAR_PROFESIONAL`, `MODIFICAR_PROFESIONAL`, `CREAR_SILLON`, `MODIFICAR_SILLON`) utilizando `RepositorioAuditoriaSqlite` (C-09).
- Verificar que los recursos dados de alta quedan inmediatamente disponibles para ser seleccionados al crear (`POST /api/v1/turnos`) o reprogramar turnos (`PATCH /api/v1/turnos/{id}/reprogramar`).

**Non-Goals:**
- Borrado físico o eliminación de recursos (la desactivación se realiza mediante `activo=False`).
- Configuración de agendas horarias o franjas de atención por profesional (`DP-08` sigue abierto para etapas posteriores).
- Bloqueo de sillón por mantenimiento (`F-12`, corresponde a `C-10 bloqueo-sillon`).

## Decisions

### D1: Métodos de persistencia en `RepositorioProfesionales` y `RepositorioSillones`
- **Decisión**:
  - `RepositorioProfesionales`:
    - `crear(nombre: str, matricula: str | None, especialidad: str | None, activo: bool = True) -> Profesional`
    - `actualizar(id_: int, nombre: str, matricula: str | None, especialidad: str | None, activo: bool) -> Profesional | None`
  - `RepositorioSillones`:
    - `crear(nombre: str, equipamiento: str | None, activo: bool = True) -> Sillon`
    - `actualizar(id_: int, nombre: str, equipamiento: str | None, activo: bool) -> Sillon | None`
- **Razón**: Permite encapsular la lógica SQL con aislamiento estricto por `tenant_id` sin acoplar la capa API a detalles de la base de datos.

### D2: Manejo de Colisiones de Unicidad y Excepciones de Dominio
- **Decisión**:
  - Declarar `RecursoDuplicadoError` en `backend/src/domain/exceptions.py`.
  - En los repositorios, capturar `sqlite3.IntegrityError` o verificar colisiones por `(tenant_id, nombre)` excluyendo el ID propio en modificaciones.
  - En la capa API, capturar `RecursoDuplicadoError` y responder HTTP 409 con código específico según la entidad (`NOMBRE_PROFESIONAL_DUPLICADO` o `NOMBRE_SILLON_DUPLICADO`).
- **Razón**: Respeta la regla de que cada clínica gestiona sus recursos de forma autónoma, pero dentro de la misma clínica los nombres deben ser unívocos para evitar confusiones en recepción y agendas.

### D3: Esquemas Pydantic de Validación
- **Decisión**:
  - `ProfesionalCrear`: `nombre` (TextoRequerido), `matricula` (str | None), `especialidad` (str | None), `activo` (bool = True).
  - `ProfesionalActualizar`: `nombre` (TextoRequerido), `matricula` (str | None), `especialidad` (str | None), `activo` (bool).
  - `SillonCrear`: `nombre` (TextoRequerido), `equipamiento` (str | None), `activo` (bool = True).
  - `SillonActualizar`: `nombre` (TextoRequerido), `equipamiento` (str | None), `activo` (bool).
  - Todos con `model_config = ConfigDict(extra="forbid")`.
- **Razón**: Mantiene la integridad del modelo impidiendo inyecciones libres de `tenant_id` y normalizando los datos de entrada.

### D4: Control de Acceso RBAC Estricto
- **Decisión**: Solo usuarios con rol `Administrador` pueden invocar los métodos `POST` y `PUT`.
  - Roles `Recepcionista` y `Profesional` reciben HTTP 403 `{"error": {"code": "ACCESO_DENEGADO", "message": "..."}}`.
  - Peticiones anónimas reciben HTTP 401 `{"error": {"code": "NO_AUTENTICADO", ...}}`.
- **Razón**: Cumple estrictamente con la matriz de permisos de `actors.md` §3 ("Gestionar profesionales: Administrador SÍ, Recepcionista NO, Profesional NO").

### D5: Integración con Bitácora de Auditoría (C-09)
- **Decisión**: Cada creación y actualización invoca `repo_auditoria.registrar()`:
  - `accion`: `CREAR_PROFESIONAL` / `MODIFICAR_PROFESIONAL` / `CREAR_SILLON` / `MODIFICAR_SILLON`.
  - `entidad`: `profesional` o `sillon`.
  - `entidad_id`: ID del recurso creado o modificado.
  - `detalle`: JSON con los atributos del recurso.
- **Razón**: Brinda trazabilidad administrativa completa y no repudio.

## Risks / Trade-offs

- **[Riesgo: Inactivar un profesional o sillón que tiene turnos futuros asignados]** → *Mitigación:* La inactivación (`activo=False`) solo impide la asignación a nuevos turnos o consultas de recursos activos. Los turnos históricos o previamente confirmados no se eliminan destructivamente (`RN-04`). La gestión integral de mantenimiento y reasignación de agenda se abordará en `C-10 bloqueo-sillon`.

## Migration Plan

1. No se requieren nuevas migraciones SQL: las tablas `profesional` y `sillon` ya cuentan con las columnas e índices necesarios creados en `001_init.sql` y `003_recursos.sql`.
2. Las rutas existentes `GET /api/v1/profesionales` y `GET /api/v1/sillones` mantienen el 100% de compatibilidad hacia atrás.
