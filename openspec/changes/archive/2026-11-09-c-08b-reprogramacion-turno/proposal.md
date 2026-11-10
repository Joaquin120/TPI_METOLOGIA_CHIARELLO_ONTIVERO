# Proposal

## Why

En la operatoria cotidiana de un consultorio o clínica odontológica, los pacientes solicitan con frecuencia modificar la fecha, el horario o los profesionales asignados a sus citas debido a imprevistos personales, emergencias o recomendaciones clínicas.

Actualmente, el sistema permite registrar turnos (`POST /api/v1/turnos`) y cambiar su estado (`PATCH /api/v1/turnos/{id}/estado`), pero carece de un mecanismo formal para reprogramar un turno existente (`F-09`). En ausencia de esta capacidad, la recepcionista se ve forzada a cancelar manualmente el turno y dar de alta uno nuevo, lo cual fragmenta el ciclo de vida del turno, destruye la trazabilidad histórica del paciente, altera su identificador único y expone la operación a inconsistencias.

Este cambio introduce la capacidad `reprogramar-turno` (Change `c-08b-reprogramacion-turno`, correspondiente a la funcionalidad `F-09`), resolviendo la regla pendiente `RP-03` mediante la **modificación in-place con auditoría**: se conserva el identificador único del turno, se valida el nuevo intervalo con el doble candado de disponibilidad simultánea e independiente (profesional y sillón/box según `RN-01`, `RN-02`, `RN-09` e intervalos semiabiertos `[inicio, fin)` según `D-07`), se libera de inmediato el horario previo para nuevas asignaciones (`RN-04`), y se registra el evento en la bitácora inmutable de auditoría (C-09) bajo estricto aislamiento multi-tenant (`RN-05`, `D-01`).

## What Changes

- **Resolución de la Regla de Negocio RP-03**:
  - Se adopta la estrategia de **modificación in-place con trazabilidad**: el turno mantiene su `id` único y sus metadatos de paciente, actualizando los campos `fecha_hora_inicio`, `fecha_hora_fin`, `profesional_id` y `sillon_id`.
  - Se preserva el estado del turno (`CONFIRMADO` o `PENDIENTE`); no se reinicia el estado salvo que explícitamente se especifique una transición posterior.
  - Se prohíbe terminantemente reprogramar turnos en estados terminales (`CANCELADO` o `COMPLETADO`), respondiendo con error de transición inválida (HTTP 409 `TRANSICION_INVALIDA`).
- **Núcleo de Dominio (`src/domain/`)**:
  - Incorporación del método `reprogramar()` en `ServicioTurnos` que verifica:
    1. Existencia del turno y pertenencia al tenant.
    2. Estado no terminal (`PENDIENTE` o `CONFIRMADO`).
    3. Doble validación simultánea e independiente de profesional y sillón en el nuevo intervalo temporal, aplicando la precedencia `RN-09` (`SolapamientoProfesionalError` prioritario ante conflicto simultáneo).
    4. **Manejo de auto-solapamiento (caso de borde)**: Al verificar solapamientos, el propio turno en reprogramación es excluido de los candidatos conflictivos para permitir desplazamientos parciales dentro de la misma franja horaria (p. ej., mover de 10:00–11:00 a 10:30–11:30 con el mismo doctor y sillón).
- **Persistencia y Adaptadores (`src/domain/puertos.py`, `src/repositories/turnos_sqlite.py`)**:
  - Ampliación de `buscar_activos_solapables` en el puerto y repositorio para admitir el parámetro opcional `excluir_turno_id: int | None = None`.
  - Incorporación del método `actualizar_reprogramacion(turno: Turno) -> Turno` en `PuertoTurnos` y `RepositorioTurnosSqlite` para actualizar de forma atómica el intervalo temporal y los recursos asignados.
- **Capa API REST (`src/api/`)**:
  - Nuevo esquema Pydantic `ReprogramarTurnoPeticion` en `backend/src/api/esquemas.py`:
    - `fecha`: str (`YYYY-MM-DD`).
    - `hora_inicio`: str (`HH:MM`).
    - `hora_fin`: str (`HH:MM`).
    - `profesional_id`: int | None (opcional; si se omite, conserva el profesional actual).
    - `sillon_id`: int | None (opcional; si se omite, conserva el sillón actual).
    - `motivo`: str | None (opcional, para registro de auditoría).
  - Nuevo endpoint `PATCH /api/v1/turnos/{id}/reprogramar` en el router `turnos.py`:
    - Retorna HTTP 200 con `TurnoRespuesta` reflejando los nuevos datos.
    - Respuestas de error estandarizadas con envelope `{"error": {"code": "...", "message": "..."}}`:
      - 401: `NO_AUTENTICADO` ante falta de token.
      - 403: `ACCESO_DENEGADO` para rol `Profesional` (restringido a `Recepcionista` y `Administrador`).
      - 404: `TURNO_NO_ENCONTRADO` si el turno no existe o pertenece a otro tenant.
      - 409: `TRANSICION_INVALIDA` (turno cancelado o completado), `SOLAPAMIENTO_PROFESIONAL` o `SOLAPAMIENTO_SILLON`.
      - 422: `VALIDACION` ante incoherencia temporal (`hora_inicio >= hora_fin`) o formato erróneo.
- **Trazabilidad y Auditoría (Integración C-09)**:
  - Registro automático del evento en la bitácora `auditoria`: `accion="REPROGRAMAR_TURNO"`, `entidad="turno"`, `entidad_id=turno.id`, registrando en `detalle` el horario y recursos previos vs. los nuevos.
- **Liberación Inmediata de Recursos**:
  - El intervalo horario previo queda liberado de inmediato en la base de datos para nuevas asignaciones de otros turnos.

## Capabilities

### New Capabilities
- `reprogramar-turno`: Reprogramación in-place de turnos existentes con validación simultánea e independiente de profesional y sillón (doble candado), liberación inmediata del horario anterior, tolerancia a desplazamientos parciales sin auto-conflicto, trazabilidad en auditoría y control de acceso RBAC multi-tenant.

### Modified Capabilities
*(Ninguna. Las capacidades existentes mantienen sus especificaciones normativas intactas).*

## Impact

- **Dominio**: Ampliación de `ServicioTurnos` y excepciones de dominio en `backend/src/domain/`.
- **Persistencia**: Actualización de la firma de `PuertoTurnos` y consulta de solapamiento en `RepositorioTurnosSqlite`.
- **Capa API**:
  - Nuevo endpoint `PATCH /api/v1/turnos/{id}/reprogramar` en `backend/src/api/routers/turnos.py`.
  - Nuevos esquemas en `backend/src/api/esquemas.py`.
- **Auditoría**: Invocación al repositorio de auditoría para registro del evento de cambio.
- **Tests**: Nueva suite de integración en `backend/tests/test_api_reprogramacion.py` y pruebas unitarias de dominio en `backend/tests/test_reprogramacion_dominio.py`.
