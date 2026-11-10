# Proposal

## Why

En la operación odontológica diaria, los sillones y boxes de atención requieren mantenimientos preventivos y correctivos, desinfecciones profundas o reparaciones técnicas periódicas (`features.md` §F-12, `flows.md` §8). Actualmente, el sistema valida solapamientos únicamente entre turnos médicos activos (`crear-turno`, `RN-01`, `RN-02`), permitiendo además inactivar sillones de forma permanente (`administrar-recursos`, `C-09b`). Sin embargo, no existe un mecanismo para programar bloqueos acotados a un intervalo horario específico (`[inicio, fin)`) sin dar de baja todo el recurso.

Este cambio introduce la capacidad `bloquear-sillon` (Change `c-10-bloqueo-sillon`, resolviendo `F-12`, `RN-07`, `RP-07` y `PA-15`), permitiendo al `Administrador` registrar bloqueos temporales con motivo justificado, garantizando que el sillón no reciba nuevos turnos ni reprogramaciones en dicho intervalo, impidiendo el bloqueo si existen turnos activos solapados (`RP-07`) para proteger las citas de los pacientes, y auditando cada acción en la bitácora inmutable (`C-09`) bajo estricto aislamiento multi-tenant.

## What Changes

- **Nueva Capacidad `bloquear-sillon`**:
  - Modelo de dominio puro `BloqueoSillon` (`id`, `tenant_id`, `sillon_id`, `fecha_hora_inicio`, `fecha_hora_fin`, `motivo`, `creado_por`, `creado_en`) en `src/domain/models.py`.
  - Excepciones de dominio en `src/domain/exceptions.py`:
    - `SillonBloqueadoError`: lanzada cuando se intenta agendar o reprogramar un turno en un sillón que posee un bloqueo temporal activo en ese intervalo semiabierto.
    - `ConflictoTurnosExistentesError`: lanzada cuando un administrador intenta registrar un bloqueo en un intervalo donde el sillón ya tiene turnos activos (`PENDIENTE` o `CONFIRMADO`), cumpliendo la salvaguarda de `RP-07`.
    - `BloqueoSolapadoError`: lanzada cuando se intenta registrar un bloqueo que se superpone con otro bloqueo ya existente en el mismo sillón.
  - Puerto de dominio `PuertoBloqueos` en `src/domain/puertos.py` con operaciones para persistir, consultar bloqueos solapados, listar por filtros y eliminar bloqueos.
  - Adaptador de persistencia SQLite `RepositorioBloqueosSqlite` en `src/repositories/bloqueos_sqlite.py` con migración `006_bloqueos.sql` (tabla `bloqueo_sillon`, claves foráneas con `tenant`, `sillon`, `usuario` e índices de intervalo).
  - Endpoints REST en `src/api/routers/bloqueos.py`:
    - `POST /api/v1/bloqueos`: registro de bloqueo temporal con motivo obligatorio. Exclusivo para rol `Administrador` (HTTP 201).
    - `GET /api/v1/bloqueos`: consulta de bloqueos filtrable por `sillon_id`, `fecha_desde` y `fecha_hasta`. Habilitado para `Administrador` y `Recepcionista` (HTTP 200).
    - `DELETE /api/v1/bloqueos/{id}`: liberación o anulación anticipada de un bloqueo. Exclusivo para rol `Administrador` (HTTP 200 con confirmación o 204).
- **Modificación de Capacidad `crear-turno`**:
  - Validación integrada en `ServicioTurnos.agendar(...)`: además de comprobar la doble disponibilidad (`RN-01`, `RN-09`), el servicio verifica que el sillón no presente bloqueos vigentes en el intervalo semiabierto `[fecha_hora_inicio, fecha_hora_fin)`.
  - Si el sillón está bloqueado, se rechaza la creación lanzando `SillonBloqueadoError` (mapeado a HTTP 409 con envelope estándar `{"error": {"code": "SILLON_BLOQUEADO", "message": "..."}}`).
- **Modificación de Capacidad `reprogramar-turno`**:
  - Validación integrada en `ServicioTurnos.reprogramar(...)`: al reprogramar hacia un nuevo intervalo/sillón, se comprueba que el sillón destino no tenga bloqueos solapados en `[nueva_inicio, nueva_fin)`.
  - Si el sillón de destino se encuentra bloqueado, se rechaza la reprogramación con `SillonBloqueadoError` (HTTP 409 `SILLON_BLOQUEADO`).
- **Trazabilidad y Auditoría (C-09)**:
  - Registro de eventos inmutables en bitácora: `CREAR_BLOQUEO_SILLON` y `ELIMINAR_BLOQUEO_SILLON` documentando usuario, sillón e intervalo.
- **Control de Acceso RBAC y Aislamiento Multi-Tenant**:
  - Creación y eliminación de bloqueos restringidas estrictamente a `Administrador`.
  - Consulta de bloqueos permitida a `Administrador` y `Recepcionista`.
  - Denegación con HTTP 403 `ACCESO_DENEGADO` para rol `Profesional`.
  - Rechazo con HTTP 401 `NO_AUTENTICADO` para solicitudes sin credenciales válidas.
  - Aislamiento multi-tenant incondicional: ningún bloqueo puede referenciar o consultar sillones de otro tenant.

## Capabilities

### New Capabilities
- `bloquear-sillon`: Gestión integral de bloqueos de sillones por mantenimiento técnico o preventivo en intervalos semiabiertos `[inicio, fin)`, validando ausencia de solapamientos con bloqueos previos, exigiendo inexistencia de turnos activos asignados (`RP-07`), con RBAC, bitácora de auditoría y aislamiento multi-tenant.

### Modified Capabilities
- `crear-turno`: La creación de turnos valida que el sillón asignado no tenga bloqueos vigentes por mantenimiento en el intervalo solicitado `[inicio, fin)`, rechazando con `SillonBloqueadoError` (HTTP 409 `SILLON_BLOQUEADO`).
- `reprogramar-turno`: La reprogramación de turnos verifica que el sillón de destino no tenga bloqueos vigentes por mantenimiento en el nuevo intervalo semiabierto, rechazando con `SillonBloqueadoError` (HTTP 409 `SILLON_BLOQUEADO`).

## Impact

- **Persistencia y Base de Datos**:
  - Nueva migración `backend/src/infrastructure/migrations/006_bloqueos.sql` con tabla `bloqueo_sillon` e índices de cobertura temporal.
  - Nuevo repositorio `backend/src/repositories/bloqueos_sqlite.py`.
- **Dominio**:
  - Nuevo modelo `BloqueoSillon` en `backend/src/domain/models.py`.
  - Nuevas excepciones en `backend/src/domain/exceptions.py`: `SillonBloqueadoError`, `ConflictoTurnosExistentesError`, `BloqueoSolapadoError`, `BloqueoNoEncontradoError`.
  - Nuevo puerto `PuertoBloqueos` en `backend/src/domain/puertos.py`.
  - Integración en `ServicioTurnos` (`agendar` y `reprogramar`).
- **Capa API**:
  - Nuevos esquemas en `backend/src/api/esquemas.py` (`BloqueoCrear`, `BloqueoRespuesta`).
  - Nuevo router `backend/src/api/routers/bloqueos.py` registrado en `backend/src/api/app.py`.
  - Mapeo de errores en `backend/src/api/errores.py`.
- **Dependencias y Pureza**:
  - Cero dependencias externas en `src/domain/` preservando el guard de pureza.
  - Compatibilidad 100% con la suite existente (273 tests).
