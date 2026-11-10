# Design

## Context

El sistema gestiona la asignación y reprogramación de turnos odontológicos con doble validación de disponibilidad (`RN-01`, `RN-02`, `RN-09`) sobre intervalos semiabiertos `[inicio, fin)` acotados a cada tenant (`RN-05`). En C-09b se implementó la baja lógica de recursos mediante el atributo `activo` en `Sillon`. Sin embargo, para mantenimientos preventivos o reparaciones temporales, inactivar el sillón de forma indefinida resulta inadecuado (`features.md` §F-12, `flows.md` §8).

Este documento detalla el diseño técnico para soportar bloqueos de sillones por intervalo temporal acotado, su persistencia, las reglas de prevención de solapamiento con turnos activos y la integración con el motor de turnos existente.

## Goals / Non-Goals

**Goals:**
- Proveer una entidad pura `BloqueoSillon` con intervalo semiabierto `[fecha_hora_inicio, fecha_hora_fin)` y motivo explícito.
- Implementar la migración de base de datos SQLite `006_bloqueos.sql` con tabla `bloqueo_sillon` e índices por tenant e intervalo.
- Implementar el repositorio `RepositorioBloqueosSqlite` cumpliendo el contrato `PuertoBloqueos`.
- Resolver formalmente `PA-15` (entidad independiente de bloqueo vs. turno especial) y `RP-07` (rechazo preventivo de bloqueo ante turnos activos solapados).
- Integrar la comprobación de sillón bloqueado en los métodos `agendar()` y `reprogramar()` de `ServicioTurnos`.
- Exponer los endpoints `POST /api/v1/bloqueos`, `GET /api/v1/bloqueos` y `DELETE /api/v1/bloqueos/{id}` con validación cronológica, control de acceso RBAC y trazabilidad en la bitácora inmutable de auditoría (C-09).

**Non-Goals:**
- Bloqueo de profesionales (médicos) por vacaciones o licencias (diferido a una etapa posterior).
- Cancelación o reprogramación automática masiva en cascada de turnos existentes al bloquear un sillón (descartado por `RP-07` para evitar pérdida silenciosa de citas médicas).
- Gestión de recurrencia periódica automática de bloqueos (ej. todos los lunes de 8 a 10).

## Decisions

### 1. Modelado: Entidad dedicada `BloqueoSillon` vs. Turno especial sin paciente (`PA-15`)

- **Decisión**: Modelar el bloqueo como una entidad dedicada e independiente `BloqueoSillon` (con su propia tabla `bloqueo_sillon`), en lugar de sobrecargar la entidad `Turno` con pacientes nulos o estados ficticios.
- **Razón**: `Turno` representa un acto médico con paciente, profesional tratante, matrícula, y un ciclo de vida asistencial (`PENDIENTE`, `CONFIRMADO`, `COMPLETADO`, `CANCELADO`). Un mantenimiento de sillón es un hecho técnico-físico del recurso que no involucra paciente ni odontólogo. Separar las entidades respeta el principio de responsabilidad única (SRP), mantiene el dominio limpio y evita que queries de agenda o métricas clínicas requieran filtros defensivos para excluir bloqueos.
- **Alternativa descartada**: Turno con `paciente_id = NULL` y `estado = BLOQUEADO`. Descartada porque rompería la invariante de no-nulidad de paciente en el modelo de turnos y contaminaría las métricas de atención clínica.

### 2. Política ante turnos existentes al crear el bloqueo (`RP-07`)

- **Decisión**: Rechazar la creación del bloqueo si existen turnos activos (`PENDIENTE` o `CONFIRMADO`) asignados a ese sillón en el intervalo solicitado (`[inicio, fin)`), lanzando `ConflictoTurnosExistentesError` (HTTP 409 `CONFLICTO_TURNOS_EXISTENTES`).
- **Razón**: En un entorno de salud, no es admisible cancelar o reubicar citas médicas de forma invisible o automática sin previa evaluación humana. Al rechazar el bloqueo, se obliga a la administración o recepción a reprogramar o cancelar conscientemente los turnos de los pacientes afectados antes de inhabilitar el sillón para mantenimiento.
- **Alternativa descartada**: Cancelación forzosa en cascada de turnos activos. Descartada por alto riesgo operativo y falta de trazabilidad con el paciente.

### 3. Detección de solapamiento e intervalos semiabiertos (`RN-02`, `D-07`)

- **Decisión**: Aplicar la misma fórmula estándar de intervalos semiabiertos `[A_inicio, A_fin)` y `[B_inicio, B_fin)`:
  ```text
  A_inicio < B_fin AND A_fin > B_inicio
  ```
- **Razón**: Permite que un turno finalice a las 10:00 y un bloqueo comience a las 10:00 (o viceversa) sin conflicto, manteniendo total consistencia con el comportamiento ya especificado y probado en toda la plataforma.

### 4. Integración en `ServicioTurnos` mediante `PuertoBloqueos`

- **Decisión**: Inyectar opcionalmente `puerto_bloqueos: PuertoBloqueos | None = None` en el constructor de `ServicioTurnos`.
- **Razón**: Mantiene retrocompatibilidad con las pruebas unitarias puras existentes del servicio, mientras que cuando se provee el puerto (en la API y tests de integración), `agendar()` y `reprogramar()` consultan `puerto_bloqueos.buscar_bloqueos_solapados(...)` inmediatamente antes de validar solapamiento de sillón. Si hay bloqueo, se lanza `SillonBloqueadoError`.

### 5. Control de Acceso RBAC y Auditoría (C-09)

- **Decisión**:
  - `POST /api/v1/bloqueos`: Exclusivo rol `Administrador`.
  - `DELETE /api/v1/bloqueos/{id}`: Exclusivo rol `Administrador`.
  - `GET /api/v1/bloqueos`: Roles `Administrador` y `Recepcionista` (recepción necesita consultar qué sillones están fuera de servicio para orientar a los pacientes).
  - Toda creación y eliminación exitosa genera un registro en la tabla de auditoría con acciones `CREAR_BLOQUEO_SILLON` y `ELIMINAR_BLOQUEO_SILLON`.

## Risks / Trade-offs

- **[Riesgo] Intentos concurrentes de crear un turno y un bloqueo en el mismo instante** → *Mitigación*: La validación se ejecuta dentro de transacciones SQLite y la comprobación de turnos activos en `crear_bloqueo` junto con la de bloqueos en `agendar` garantizan la coherencia temporal.
- **[Riesgo] Bloqueos históricos acumulados en base de datos** → *Mitigación*: Se agregan índices compuestos `(tenant_id, sillon_id, fecha_hora_inicio, fecha_hora_fin)` para asegurar búsquedas O(log N) eficientes sin degradación de rendimiento.

## Migration Plan

1. Ejecutar script de migración `backend/src/infrastructure/migrations/006_bloqueos.sql` para crear la tabla `bloqueo_sillon` e índices.
2. Actualizar `backend/src/infrastructure/database.py` para incluir `006_bloqueos.sql` en la secuencia de inicialización `migrar()`.
3. Rollback: En caso de requerirse reversión, la tabla `bloqueo_sillon` puede descartarse con `DROP TABLE IF EXISTS bloqueo_sillon` sin afectar a `turno`, `profesional` ni `sillon`.
