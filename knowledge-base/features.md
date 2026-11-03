# Especificación de Funcionalidades y Endpoints

Este documento cataloga las funcionalidades del producto por módulo y etapa. Cada funcionalidad indica actor, reglas asociadas y criterios de aceptación. Los flujos paso a paso se desarrollan en [flows.md](flows.md) y las reglas normativas en [business-rules.md](business-rules.md).

## 1. Criterios de catalogación

- **Etapa:** `MVP`, `Segunda etapa` o `Futuro`. La etapa indica cuándo se espera construir, no el estado actual del código.
- **ID:** `F-XX`, estable y referenciable desde otros documentos.
- **Actor:** rol que inicia o recibe la funcionalidad.
- **Reglas:** reglas de negocio que la funcionalidad debe respetar.
- **Criterio de aceptación:** condición observable que permite verificar que la funcionalidad cumple su propósito.

## 2. Catálogo por módulo

### 2.1. Agenda y Turnos

| ID | Funcionalidad | Actor | Etapa | Reglas |
|---|---|---|---|---|
| **F-01** | Registrar turno con doble validación | Recepcionista | MVP | `RN-01`, `RN-02`, `RN-09` |
| **F-02** | Consultar y filtrar turnos | Recepcionista / Profesional | MVP | `RN-05` |
| **F-03** | Cambiar el estado de un turno | Recepcionista | MVP | `RN-03`, `RN-04` |
| **F-09** | Reprogramar un turno | Recepcionista | MVP (detalle pendiente) | `RN-01` a `RN-04` |
| **F-06** | Visualizar agenda matricial | Recepcionista / Profesional | Segunda etapa | `RN-01` |
| **F-08** | Gestionar lista de espera | Recepcionista | Segunda etapa | `RN-04` |

### 2.2. Recursos

| ID | Funcionalidad | Actor | Etapa | Reglas |
|---|---|---|---|---|
| **F-04** | Consultar profesionales | Recepcionista | MVP | `RN-05` |
| **F-05** | Consultar sillones/boxes | Recepcionista | MVP | `RN-05` |
| **F-10** | Administrar profesionales, sillones y horarios | Administrador | MVP (endpoints pendientes) | `RN-05` |
| **F-12** | Bloquear un sillón por mantenimiento | Administrador | MVP (propuesta) | `RN-07` |

### 2.3. Pacientes

| ID | Funcionalidad | Actor | Etapa | Reglas |
|---|---|---|---|---|
| **F-11** | Gestionar pacientes | Pendiente de definición | MVP (endpoints pendientes) | `RN-05`, `RN-06` |

### 2.4. Notificaciones

| ID | Funcionalidad | Actor | Etapa | Reglas |
|---|---|---|---|---|
| **F-07** | Enviar recordatorios y solicitar confirmación | Sistema | Segunda etapa | `RN-03`, `RN-04` |

### 2.5. Módulos futuros

| ID | Funcionalidad | Actor | Etapa | Observaciones |
|---|---|---|---|---|
| **F-13** | Odontograma y ficha periodontal | Profesional | Futuro | Fuera del MVP |
| **F-14** | Facturación electrónica AFIP/ARCA | Administrador | Futuro | Alcance pendiente (`PA-03`) |
| **F-15** | Liquidación de honorarios | Administrador | Futuro | Fuera del MVP |
| **F-16** | Control de inventario de insumos | Administrador | Futuro | Fuera del MVP |

## 3. Detalle de funcionalidades del MVP

### F-01 — Registrar turno con doble validación

**Actor:** Recepcionista.

**Precondiciones:**

- El paciente, el profesional y el sillón existen en el tenant.
- La fecha y el horario están definidos.

**Flujo principal:**

1. La recepcionista envía los datos del turno.
2. El sistema normaliza el intervalo como `[inicio, fin)`.
3. Verifica la disponibilidad del profesional.
4. Verifica la disponibilidad del sillón.
5. Si ambos están libres, registra el turno.
6. Devuelve el turno creado con su estado.

**Excepciones:**

- Profesional ocupado: `SolapamientoProfesionalError`.
- Sillón ocupado: `SolapamientoSillonError`.
- Ambos ocupados: `SolapamientoProfesionalError` por `RN-09`.

**Criterios de aceptación:**

- Un turno sin conflicto se registra correctamente.
- Un turno que se solapa con otro del mismo profesional se rechaza aunque cambie el sillón.
- Un turno que se solapa con otro del mismo sillón se rechaza aunque cambie el profesional.
- Un turno contiguo en el límite exacto se acepta.
- Un turno rechazado no queda registrado.

**Trazabilidad:** `openspec/specs/crear-turno/spec.md`, `RN-01`, `RN-02`, `RN-09`.

### F-02 — Consultar y filtrar turnos

**Actor:** Recepcionista o Profesional.

**Descripción:** permite listar turnos y filtrarlos por profesional, sillón y fecha. El profesional solo puede consultar los turnos propios.

**Filtros previstos:**

| Filtro | Tipo | Obligatorio |
|---|---|---|
| `profesional_id` | Identificador | No |
| `sillon_id` | Identificador | No |
| `fecha` | Fecha | No |

**Criterio de aceptación:** la respuesta contiene únicamente turnos del tenant y respeta los filtros solicitados.

### F-03 — Cambiar el estado de un turno

**Actor:** Recepcionista para confirmar y cancelar. La finalización (`COMPLETADO`) queda pendiente de asignación de rol.

**Descripción:** aplica las transiciones válidas de `RN-03`.

| Acción | Estado origen | Estado destino |
|---|---|---|
| Confirmar | `PENDIENTE` | `CONFIRMADO` |
| Cancelar | `PENDIENTE` o `CONFIRMADO` | `CANCELADO` |
| Completar | `CONFIRMADO` | `COMPLETADO` |

**Criterio de aceptación:** una transición no permitida se rechaza y no modifica el estado del turno. La cancelación libera los recursos de inmediato.

### F-09 — Reprogramar un turno

**Actor:** Recepcionista.

**Descripción:** permite mover un turno existente a otro horario, profesional o sillón, respetando el doble candado.

**Estado:** funcionalidad prevista en el MVP, pero el mecanismo no está definido. Queda pendiente decidir si se implementa como cancelación + alta o como modificación del turno (`RP-03`), y definir el endpoint correspondiente.

**Criterios de aceptación preliminares:**

- El nuevo horario no debe solaparse con otro turno activo del profesional ni del sillón.
- El horario anterior debe quedar liberado.
- Debe conservarse la trazabilidad de la reprogramación.

### F-04 — Consultar profesionales

**Actor:** Recepcionista.

**Descripción:** devuelve la lista de profesionales del tenant para asignarlos a un turno.

**Criterio de aceptación:** la lista solo incluye profesionales del tenant de la sesión.

### F-05 — Consultar sillones/boxes

**Actor:** Recepcionista.

**Descripción:** devuelve la lista de sillones del tenant, incluyendo su estado activo/inactivo y equipamiento.

**Criterio de aceptación:** la lista solo incluye sillones del tenant. El tratamiento exacto de los sillones inactivos está pendiente (`PA-01`).

### F-10 — Administrar profesionales, sillones y horarios

**Actor:** Administrador.

**Descripción:** alta y edición de profesionales y sillones; configuración de horarios de atención. La baja lógica o inactivación de recursos queda pendiente (`DP-06`, `PA-16`).

**Estado:** funcionalidad prevista en el MVP, pero los endpoints y el modelo de horarios están pendientes de definición (`DP-08`).

**Criterios de aceptación preliminares:**

- Un profesional creado queda disponible para asignar turnos.
- Un sillón creado queda disponible para asignar turnos.
- El tratamiento de un recurso inactivo está pendiente (`PA-01`).

### F-11 — Gestionar pacientes

**Actor:** Pendiente de definición; el alta y la consulta están previstas en el MVP, pero el rol que las ejecuta no está confirmado (ver [actors.md](actors.md)).

**Descripción:** alta y consulta de pacientes con los datos mínimos definidos en [data-models.md](data-models.md).

**Estado:** funcionalidad prevista en el MVP, pero los endpoints y el alcance de edición están pendientes de definición.

**Criterio de aceptación preliminar:** un paciente creado puede asociarse a un turno del mismo tenant.

### F-12 — Bloquear un sillón por mantenimiento

**Actor:** Administrador.

**Descripción:** impide que un sillón reciba turnos durante un intervalo. El mecanismo —turno de bloqueo o inactivación— está pendiente de modelado (`PA-15`, `PA-16`).

**Criterio de aceptación propuesto:** el sillón bloqueado no puede asignarse a un turno nuevo en el intervalo afectado; el mecanismo definitivo está pendiente (`PA-15`, `PA-16`).

**Pendiente:** definir el modelo del turno de bloqueo, quién autoriza, cómo se visualiza, cómo se libera y qué ocurre con los turnos ya asignados (`PA-01`, `PA-15`, `PA-16`, `RP-07`).

## 4. Funcionalidades de la segunda etapa

### F-06 — Visualizar agenda matricial

Vista cruzada de profesionales y sillones por franja horaria, con estados por color e indicación de solapamientos. Requiere definir la granularidad de la grilla y los filtros.

### F-07 — Enviar recordatorios y solicitar confirmación

Envío automático de recordatorios por WhatsApp y recepción de la confirmación o cancelación del paciente. Requiere definir proveedor, momentos de envío, plantillas y opt-in (`PA-11`, `DP-09`).

### F-08 — Gestionar lista de espera

Registro de pacientes interesados en un horario ocupado y reasignación ante cancelaciones. Requiere definir reglas de prioridad y notificación.

## 5. Endpoints

| Método | Ruta | Propósito | Etapa | Estado |
|---|---|---|---|---|
| `GET` | `/api/v1/turnos` | Listar turnos con filtros | MVP | Definido |
| `POST` | `/api/v1/turnos` | Registrar un turno | MVP | Definido |
| `PATCH` | `/api/v1/turnos/{id}/estado` | Cambiar el estado de un turno | MVP | Definido |
| `GET` | `/api/v1/profesionales` | Listar profesionales | MVP | Definido |
| `GET` | `/api/v1/sillones` | Listar sillones | MVP | Definido |
| — | — | Reprogramar un turno | MVP | Pendiente de definición |
| — | — | Consultar disponibilidad de recursos | No definido | Pendiente de definición |
| — | — | Alta de paciente | MVP | Pendiente de definición |
| — | — | Alta de profesional | MVP | Pendiente de definición |
| — | — | Alta de sillón | MVP | Pendiente de definición |

### 5.1. Ejemplo ilustrativo de alta de turno

> El contrato definitivo está pendiente. El ejemplo usa los campos del modelo de datos y no incluye `tenant_id` porque el tenant se resuelve desde la sesión.

```json
{
  "paciente_id": "pac-001",
  "profesional_id": "prof-001",
  "sillon_id": "sillon-001",
  "fecha_hora_inicio": "2026-11-01T10:00:00",
  "fecha_hora_fin": "2026-11-01T10:30:00"
}
```

Respuesta esperada:

```json
{
  "id": "turno-001",
  "paciente_id": "pac-001",
  "profesional_id": "prof-001",
  "sillon_id": "sillon-001",
  "fecha_hora_inicio": "2026-11-01T10:00:00",
  "fecha_hora_fin": "2026-11-01T10:30:00",
  "estado": "CONFIRMADO"
}
```

> El estado `CONFIRMADO` refleja la especificación vigente; el estado inicial del alta sigue pendiente de definición (`PA-13`).

### 5.2. Errores de dominio

| Excepción | Causa | Código HTTP |
|---|---|---|
| `SolapamientoProfesionalError` | El profesional ya tiene un turno activo en el intervalo. | Pendiente de definición |
| `SolapamientoSillonError` | El sillón ya tiene un turno activo en el intervalo. | Pendiente de definición |

El mapeo de excepciones a códigos HTTP forma parte del contrato de la API y todavía no está definido.

## 6. Trazabilidad

| Funcionalidad | Regla | Especificación | Pruebas esperadas |
|---|---|---|---|
| `F-01` | `RN-01`, `RN-02`, `RN-09` | `openspec/specs/crear-turno/spec.md` | Camino feliz, conflicto de profesional, conflicto de sillón, contiguos |
| `F-02` | `RN-05` | Pendiente | Filtros y aislamiento por tenant |
| `F-03` | `RN-03`, `RN-04` | Pendiente | Transiciones válidas e inválidas |
| `F-04` | `RN-05` | Pendiente | Listado acotado al tenant |
| `F-05` | `RN-05` | Pendiente | Listado acotado al tenant y estado del sillón |
| `F-06` | `RN-01` | Pendiente | Vista por profesional y sillón (segunda etapa) |
| `F-07` | `RN-03`, `RN-04` | Pendiente | Recordatorio, confirmación y cancelación del paciente (segunda etapa) |
| `F-08` | `RN-04` | Pendiente | Reasignación ante cancelaciones (segunda etapa) |
| `F-09` | `RN-01` a `RN-04` | Pendiente | Nuevo horario sin solapamiento y liberación del anterior |
| `F-10` | `RN-05` | Pendiente | Alta y edición de recursos; horarios pendientes (`DP-08`) |
| `F-11` | `RN-05`, `RN-06` | Pendiente | Paciente asociado a un turno del mismo tenant |
| `F-12` | `RN-07` | Pendiente | Bloqueo e inactivación (modelo pendiente: `PA-15`, `PA-16`, `RP-07`) |

## 7. Funcionalidades pendientes de definición

- Consulta de disponibilidad antes de crear el turno.
- Contrato de reprogramación.
- Endpoints de pacientes y de administración de recursos.
- Modelo de turno de bloqueo y baja lógica de recursos (`PA-15`, `PA-16`).
- Gestión de horarios y feriados.
- Reglas de lista de espera.
- Condiciones de notificación y opt-in.
- Portal del paciente.

## 8. Documentos relacionados

- [flows.md](flows.md) — desarrollo paso a paso.
- [actors.md](actors.md) — permisos por rol.
- [business-rules.md](business-rules.md) — reglas aplicadas.
- [data-models.md](data-models.md) — entidades y campos.
- [open-questions.md](open-questions.md) — definiciones pendientes.
