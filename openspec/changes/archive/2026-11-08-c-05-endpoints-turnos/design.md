# Design

## UI Mockups
Decision: no (no UI)

## Context
Véase [proposal.md](proposal.md) para la motivación general del change.
El sistema cuenta actualmente con:
- Dominio puro (`src/domain/services.py`, `models.py`, `puertos.py`) que ya implementa la matriz de transiciones válidas (`RN-03`), las reglas de solapamiento en intervalos semiabiertos (`RN-01`, `RN-02`, `RN-09`) y la exclusión de turnos cancelados en consultas de recursos (`RN-04`).
- Repositorio SQLite (`src/repositories/turnos_sqlite.py`) con aislamiento por `tenant_id` y métodos básicos `guardar`, `actualizar`, `listar` (sin filtros) y `buscar_activos_solapables`.
- Capa HTTP FastAPI (`src/api/routers/turnos.py`, `dependencias.py`, `esquemas.py`) que resuelve autenticación JWT (`ContextoUsuario`), RBAC (`requerir_rol`) y serialización, pero aún no expone filtros de consulta ni el endpoint de cambio de estado.

## Goals / Non-Goals

**Goals:**
- Extender `GET /api/v1/turnos` con soporte de parámetros de consulta opcionales (`fecha`, `profesional_id`, `sillon_id`) aplicando conjunción lógica (AND) parametrizada en SQL.
- Implementar la restricción de visibilidad de agenda para usuarios con rol `Profesional` en `GET /api/v1/turnos`: únicamente acceden a turnos donde `profesional_id` coincida con su identidad autenticada.
- Exponer `PATCH /api/v1/turnos/{id}/estado` recibiendo una acción normativa (`confirmar`, `cancelar`, `completar`), protegido para roles `Recepcionista` y `Administrador`.
- Manejar respuestas y errores con el envelope estándar: `404 TURNO_NO_ENCONTRADO` si el turno no existe en el tenant, `409 TRANSICION_INVALIDA` si el dominio rechaza la transición, `403 ACCESO_DENEGADO` ante roles no autorizados, y `422 VALIDACION` ante formatos o acciones inválidas.
- Preservar la pureza absoluta del dominio (0 imports de frameworks o infraestructura en `src/domain/`).

**Non-Goals:**
- Paginación o cursores de turnos (diferido a etapas posteriores).
- Reprogramación de turnos (`F-09` / `RP-03`: cancel + create vs update queda en change posterior).
- Modificación del estado inicial de alta (`PA-13`: se mantiene `CONFIRMADO` como establece la spec vigente).
- UI o vistas frontend (este change es estrictamente backend API).

## Decisions

### D-01: Decisión de UI
Decision: no (no UI). El change corresponde a endpoints de backend REST sin superficie visual.

### D-02: Filtros de consulta y construcción de SQL en el repositorio
- **Elección**: Extender la firma de `listar` en `PuertoTurnos` y `RepositorioTurnosSqlite` con parámetros opcionales `fecha: str | None = None`, `profesional_id: int | None = None`, `sillon_id: int | None = None`.
- **Implementación SQL**: Construcción dinámica de cláusulas `AND` con tupla de parámetros posicionales (`?`), manteniendo siempre como predicado raíz `tenant_id = ?`.
  - Si `fecha` está presente: `AND t.fecha_hora_inicio LIKE ?` (ej. `'2026-11-01%'`) o extracción de fecha. Dado que `fecha_hora_inicio` se almacena como `YYYY-MM-DD HH:MM`, filtrar con `t.fecha_hora_inicio >= ? AND t.fecha_hora_inicio <= ?` o `substr(t.fecha_hora_inicio, 1, 10) = ?`. El uso de `substr(t.fecha_hora_inicio, 1, 10) = ?` o `t.fecha_hora_inicio LIKE ?` garantiza precisión y compatibilidad SQLite.
  - Si `profesional_id` está presente: `AND t.profesional_id = ?`.
  - Si `sillon_id` está presente: `AND t.sillon_id = ?`.
- **Alternativa descartada**: Filtrar en memoria en Python tras cargar todos los turnos del tenant. Se descarta porque delega a la base de datos la selección eficiente y evita transferencias innecesarias.

### D-03: Restricción de visibilidad para rol Profesional
- **Elección**: En el router de turnos, si el usuario autenticado tiene rol `Profesional`, se valida su `profesional_id`. Si la query especifica un `profesional_id` diferente al suyo, se lanza `403 ACCESO_DENEGADO`. Si no se especifica, se fuerza automáticamente `profesional_id = usuario.profesional_id`.
- **Razón**: Cumple estrictamente con la matriz de permisos (`knowledge-base/actors.md` §3 y `RN-05`) impidiendo la fuga de información o espionaje de agendas entre profesionales dentro de la misma clínica.

### D-04: Contrato de `PATCH /api/v1/turnos/{id}/estado`
- **Elección**: Esquema Pydantic `TurnoCambioEstado` con un campo obligatorio `accion: Literal["confirmar", "cancelar", "completar"]` y `extra="forbid"`.
- **Flujo de ejecución**:
  1. FastAPI valida el token JWT y el rol del usuario (`Recepcionista` o `Administrador`).
  2. Se consulta el turno por `(id, tenant_id)` usando `repositorio.obtener_por_id(id)`. Si es `None`, se lanza `HTTPException(404, {"error": {"code": "TURNO_NO_ENCONTRADO", "message": "Turno no encontrado"}})` vía `ErrorTurnoNoEncontrado`.
  3. Se despacha a `servicio.confirmar(turno)`, `servicio.cancelar(turno)` o `servicio.completar(turno)` según la acción.
  4. Si el dominio lanza `TransicionInvalidaError`, el exception handler global de la API (definido en C-03/C-04) lo captura y responde `409 TRANSICION_INVALIDA`.
  5. Se retorna el `TurnoRespuesta.desde_dominio(turno_actualizado)` con código `200`.
- **Alternativas descartadas**:
  - Enviar `nuevo_estado: str`: La transición por acción modela mejor la intención del negocio y se mapea 1:1 con los métodos del servicio de dominio sin lógica condicional dispersa.

### D-05: Liberación de recursos en cancelación (`RN-04`)
- El método `buscar_activos_solapables` en SQLite ya filtra por `estado IN ('PENDIENTE', 'CONFIRMADO')`. Al transicionar a `CANCELADO` mediante `servicio.cancelar(turno)`, el turno permanece en la tabla con `estado = 'CANCELADO'`, dejando de bloquear inmediatamente al profesional y al sillón para agendar en ese intervalo. Esto ya está desacoplado y garantizado en persistencia y dominio.

## Risks / Trade-offs

- **[Riesgo] Discrepancia entre `profesional_id` del token y el recurso**: Si un usuario tiene rol `Profesional` pero no tiene `profesional_id` asignado en la base/token.
  - *Mitigación*: Validación en el router: si el rol es `Profesional` y `usuario.profesional_id is None`, rechazar con `403 ACCESO_DENEGADO` ("Usuario profesional sin recurso asociado").
- **[Riesgo] Desfase en formato de fecha en query**: Si el cliente envía fechas no ISO o mal formateadas.
  - *Mitigación*: Validación estricta con Pydantic / FastAPI Query usando `pattern=PATRON_FECHA` (`^\d{4}-\d{2}-\d{2}$`) que devuelve `422 VALIDACION` con envelope uniforme.

