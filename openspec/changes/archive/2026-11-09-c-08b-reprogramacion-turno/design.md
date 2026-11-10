# Design

## Context

El sistema turnos-odontologia cuenta con servicios de agendamiento, máquina de estados, persistencia relacional en SQLite, autenticación JWT, RBAC, endpoints REST, gestión de pacientes, métricas y auditoría (C-01 a C-09).

Actualmente, cambiar el horario o los recursos asignados a un turno no cuenta con un camino estructurado en la API: la única alternativa disponible es cancelar el turno (`PATCH /api/v1/turnos/{id}/estado`) y registrar un nuevo turno (`POST /api/v1/turnos`), lo que destruye el identificador del turno y desconecta la trazabilidad (`PA-06`).

Ver `proposal.md` para la motivación general del cambio y `specs/reprogramar-turno/spec.md` para los requisitos normativos y escenarios Given/When/Then.

## Goals / Non-Goals

**Goals:**
- Resolver formalmente la regla de negocio `RP-03` implementando la reprogramación in-place del turno.
- Preservar el identificador único `id`, el paciente y el estado activo (`PENDIENTE` o `CONFIRMADO`) del turno.
- Garantizar la doble validación simultánea e independiente de profesional y sillón (`RN-01`, `RN-02`, `RN-09`, `D-07`) en el nuevo intervalo semiabierto `[hora_inicio, hora_fin)`.
- Soportar desplazamientos de horario que solapen con la franja original del propio turno excluyendo su propio ID (`excluir_turno_id`).
- Liberar de inmediato el intervalo horario previo para que quede disponible para otros turnos (`RN-04`).
- Prohibir la reprogramación de turnos en estados terminales (`CANCELADO` o `COMPLETADO`) según la matriz de estados.
- Exponer el endpoint REST `PATCH /api/v1/turnos/{id}/reprogramar` protegido por RBAC (`Recepcionista` y `Administrador`).
- Registrar el evento en la bitácora inmutable de auditoría (C-09) bajo aislamiento multi-tenant estricto.

**Non-Goals:**
- Reprogramación en lote o periódica (fuera del alcance del MVP).
- Notificaciones automáticas por WhatsApp al paciente (corresponde a Fase 5, C-14).
- Modificación de datos filiatorios del paciente durante la reprogramación (los datos del paciente se gestionan mediante C-07).

## Decisions

### D1: Modificación In-Place con Trazabilidad (Resolución de RP-03)
- **Decisión**: El turno se actualiza in-place en la tabla `turno` conservando su `id`. Se actualizan los campos `fecha_hora_inicio`, `fecha_hora_fin`, `profesional_id` y `sillon_id`.
- **Alternativa descartada**: Cancelación + Alta automática. Se descartó porque provocaría la pérdida del identificador comunicado previamente al paciente, generaría registros huérfanos y distorsionaría las métricas de cancelación calculadas en C-08.

### D2: Algoritmo de Detección de Solapamiento con Auto-Exclusión (`excluir_turno_id`)
- **Decisión**: Extender `buscar_activos_solapables` en `PuertoTurnos` y `RepositorioTurnosSqlite` para aceptar un argumento opcional `excluir_turno_id: int | None = None`. En la consulta SQL, se agrega la condición:
  ```sql
  AND (? IS NULL OR t.id != ?)
  ```
- **Razón**: Si un paciente reprograma su turno de 10:00–11:00 a 10:30–11:30 con el mismo odontólogo y sillón, el intervalo nuevo comparte 30 minutos con el turno original. Sin la exclusión del ID propio, la validación detectaría falsamente un solapamiento consigo mismo (auto-bloqueo).

### D3: Contrato HTTP REST `PATCH /api/v1/turnos/{id}/reprogramar`
- **Decisión**: Exponer el endpoint `PATCH /api/v1/turnos/{id}/reprogramar`.
  - Cuerpo JSON:
    ```json
    {
      "fecha": "2026-11-02",
      "hora_inicio": "14:00",
      "hora_fin": "14:30",
      "profesional_id": 1,
      "sillon_id": 1,
      "motivo": "Solicitud de cambio por el paciente"
    }
    ```
    Los campos `profesional_id` y `sillon_id` son opcionales: si no se envían, se mantienen los recursos actuales del turno.
  - Respuesta HTTP 200 con el esquema `TurnoRespuesta`.
- **Alternativa descartada**: `PUT /api/v1/turnos/{id}` (reemplazo completo) o `POST /api/v1/turnos/{id}/reprogramar`. `PATCH` es consistente con `PATCH /api/v1/turnos/{id}/estado`.

### D4: Respeto Estricto de Estados Terminales (Domain State Matrix)
- **Decisión**: Un turno en estado `CANCELADO` o `COMPLETADO` no admite reprogramación.
  - Si se intenta reprogramar un turno terminal, el servicio de dominio lanza `TransicionInvalidaError(f"No se puede reprogramar un turno en estado '{turno.estado}'")`, mapeándose a HTTP 409 con envelope `{"error": {"code": "TRANSICION_INVALIDA", "message": "..."}}`.
- **Razón**: Los estados finales son terminales y absorbentes según `RN-03` y `data-models.md` §4.1.

### D5: Integración con la Bitácora de Auditoría (C-09)
- **Decisión**: Cuando la reprogramación se confirma, se registra en `RepositorioAuditoriaSqlite`:
  - `accion`: `"REPROGRAMAR_TURNO"`
  - `entidad`: `"turno"`
  - `entidad_id`: `turno.id`
  - `detalle`: JSON con `"anterior"` (`fecha`, `horas`, `profesional`, `sillon`) y `"nuevo"` (`fecha`, `horas`, `profesional`, `sillon`, `motivo`).
- **Razón**: Proporciona no repudio y trazabilidad completa del ciclo de vida del turno.

### D6: Control de Acceso RBAC y Aislamiento Multi-Tenant
- **Decisión**:
  - Exclusivo para roles `Recepcionista` y `Administrador`.
  - Rol `Profesional` recibe HTTP 403 `{"error": {"code": "ACCESO_DENEGADO", "message": "..."}}`.
  - Peticiones sin token reciben HTTP 401 `{"error": {"code": "NO_AUTENTICADO", "message": "..."}}`.
  - Todas las consultas y actualizaciones filtran incondicionalmente por el `tenant_id` resuelto desde el JWT. Si el turno solicitado no existe o pertenece a otro tenant, se responde HTTP 404 `{"error": {"code": "TURNO_NO_ENCONTRADO", "message": "..."}}`.

## Risks / Trade-offs

- **[Riesgo: Condición de carrera en reprogramaciones concurrentes hacia el mismo horario]** → *Mitigación:* Se ejecuta la verificación y actualización dentro de la misma transacción en SQLite con nivel de aislamiento serializable o control transaccional del repositorio.
- **[Riesgo: Parámetros opcionales omitidos causen inconsistencia de recursos]** → *Mitigación:* Si `profesional_id` o `sillon_id` son `None`, el servicio recupera explícitamente los recursos vigentes del turno antes de verificar solapamientos.

## Migration Plan

1. El cambio no altera la estructura de tablas de la base de datos (las columnas `fecha_hora_inicio`, `fecha_hora_fin`, `profesional_id` y `sillon_id` ya existen en `turno`).
2. La compatibilidad hacia atrás es del 100%: los endpoints existentes (`POST /api/v1/turnos`, `GET /api/v1/turnos`, `PATCH /api/v1/turnos/{id}/estado`) conservan su comportamiento íntegro.
