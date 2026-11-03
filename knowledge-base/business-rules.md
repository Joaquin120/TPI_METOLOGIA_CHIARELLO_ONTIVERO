# Reglas del Dominio Odontológico

Este documento es la fuente normativa del dominio. Define qué está permitido, qué se rechaza y qué efectos tienen las transiciones de estado. Las funcionalidades que aplican estas reglas se catalogan en [features.md](features.md) y se desarrollan paso a paso en [flows.md](flows.md).

## 1. Definiciones

| Término | Definición |
|---|---|
| **Turno** | Reserva temporal de dos recursos simultáneos: un profesional y un sillón/box, para un paciente, en un intervalo de fecha y hora. |
| **Turno activo** | Turno en estado `PENDIENTE` o `CONFIRMADO`. Es el único tipo de turno que bloquea recursos. |
| **Recurso** | Cualquier elemento finito necesario para la atención: profesional o sillón/box. |
| **Solapamiento** | Intersección temporal no vacía entre dos turnos activos sobre el mismo recurso. |
| **Intervalo semiabierto** | Rango `[inicio, fin)` en el que el extremo inicial está incluido y el final excluido. |
| **Tenant** | Clínica o consultorio aislado dentro de la plataforma SaaS. |
| **Bloqueo** | Periodo en el que un recurso no está disponible por un motivo distinto de la atención de un paciente, por ejemplo mantenimiento. Su representación —turno de bloqueo, inactivación u otra— está pendiente de definición (`PA-15`, `PA-16`). |

## 2. Entidades principales

| Entidad | Rol en el dominio |
|---|---|
| **Profesional** | Odontólogo matriculado que atiende el turno. |
| **Sillón / Box** | Recurso físico donde se realiza la atención. |
| **Paciente** | Persona que recibe la atención. |
| **Turno** | Reserva que relaciona paciente, profesional, sillón y horario. |
| **Tenant** | Clínica o consultorio propietario de los datos. |

El detalle de campos y relaciones está en [data-models.md](data-models.md).

## 3. Reglas de negocio

| ID | Regla | Descripción | Etapa |
|---|---|---|---|
| **RN-01** | Doble candado | Un turno solo se registra si el profesional y el sillón están libres de forma simultánea e independiente. | MVP |
| **RN-02** | Intervalos semiabiertos | Dos turnos se solapan si `inicio_a < fin_b` y `fin_a > inicio_b`. Si `fin_a == inicio_b`, son contiguos y válidos. | MVP |
| **RN-03** | Ciclo de estados | Solo se permiten las transiciones definidas entre `PENDIENTE`, `CONFIRMADO`, `CANCELADO` y `COMPLETADO`. | MVP |
| **RN-04** | Liberación por cancelación | Un turno cancelado libera de inmediato al profesional y al sillón. | MVP |
| **RN-05** | Aislamiento por tenant | Toda consulta y validación se ejecuta dentro del tenant de la clínica. | MVP |
| **RN-06** | Datos sintéticos y privacidad | No se almacenan datos reales de pacientes o profesionales en el repositorio, pruebas o ejemplos. | Transversal |
| **RN-07** | Bloqueo de sillón | El MVP prevé bloquear un sillón por mantenimiento; la clasificación es una propuesta pendiente de validación y el mecanismo (turno de bloqueo o inactivación) y su modelo están pendientes (`PA-15`, `PA-16`). | MVP (propuesta) |
| **RN-08** | Sin sobreturnos en el MVP | No se permiten excepciones de sobreposición por urgencias en el MVP. | MVP |
| **RN-09** | Precedencia de validación | Si un turno entra en conflicto con el mismo profesional y el mismo sillón, se informa primero el conflicto de profesional. | MVP |

### RN-01 — Doble candado

**Condición:** se solicita registrar un turno para un paciente, un profesional y un sillón en una fecha y horario determinados.

**Validación:** el sistema debe comprobar, de forma simultánea e independiente:

1. Que no exista otro turno activo del mismo profesional que se solape con el intervalo solicitado.
2. Que no exista otro turno activo del mismo sillón que se solape con el intervalo solicitado.

**Resultado:**

- Si ambos recursos están libres, el turno se registra.
- Si el profesional está ocupado, se rechaza con `SolapamientoProfesionalError`.
- Si el sillón está ocupado, se rechaza con `SolapamientoSillonError`.
- Si ambos están ocupados, se aplica `RN-09`.

**Efecto:** un turno rechazado no se persiste ni bloquea recursos.

### RN-02 — Intervalos semiabiertos

Dos intervalos `A = [A_inicio, A_fin)` y `B = [B_inicio, B_fin)` se solapan si y solo si:

```text
A_inicio < B_fin  AND  A_fin > B_inicio
```

Consecuencias:

- `A_fin == B_inicio` **no** es solapamiento: los turnos son contiguos.
- `A_inicio == B_inicio` es solapamiento para turnos con duración positiva; el tratamiento de duraciones cero o negativas está pendiente (`RP-01`).
- El mismo horario en fechas distintas no genera conflicto.

### RN-03 — Ciclo de estados

| Estado actual | Acción | Estado destino | Efecto sobre recursos |
|---|---|---|---|
| `PENDIENTE` | Confirmar | `CONFIRMADO` | Mantiene reservados el profesional y el sillón, que ya estaban bloqueados desde `PENDIENTE` |
| `PENDIENTE` | Cancelar | `CANCELADO` | Libera profesional y sillón |
| `CONFIRMADO` | Completar | `COMPLETADO` | Libera los recursos al cerrar la atención |
| `CONFIRMADO` | Cancelar | `CANCELADO` | Libera profesional y sillón |
| `CANCELADO` | — | — | Estado final; no admite transiciones |
| `COMPLETADO` | — | — | Estado final; no admite transiciones |

El estado inicial del alta está pendiente de definición (`PA-13`): la especificación vigente registra el turno como `CONFIRMADO`, mientras que el ciclo de vida contempla `PENDIENTE`.

### RN-04 — Liberación por cancelación

Al pasar a `CANCELADO`, el turno deja de considerarse activo. A partir de ese momento:

- El profesional queda disponible para ese intervalo.
- El sillón queda disponible para ese intervalo.
- El turno cancelado se conserva como historial, pero no bloquea nuevas reservas.

### RN-05 — Aislamiento por tenant

- Todo profesional, sillón, paciente y turno pertenece a un tenant.
- Las validaciones de solapamiento se realizan solo contra turnos del mismo tenant.
- Un turno no puede referenciar recursos de otro tenant.
- La estrategia física de aislamiento está pendiente de definición (`DP-03`).

### RN-06 — Datos sintéticos y privacidad

- Los ejemplos, pruebas y datos de demostración usan nombres ficticios como `Dr. Pérez`, `Paciente A` o `Sillón 1`.
- No se almacenan datos reales de pacientes ni de profesionales.
- La política de retención y tratamiento de datos productivos está pendiente de definición (`PA-12`).

### RN-07 — Bloqueo de sillón

Para el MVP —clasificación propuesta, pendiente de validación— se prevén dos formas de dejar un sillón fuera de servicio:

1. Registrar un turno de bloqueo que ocupe el intervalo afectado.
2. Inactivar el recurso `Sillon` para que no se ofrezca en la agenda.

Ninguno de los dos mecanismos está modelado todavía. El modelo del turno de bloqueo (`PA-15`), la baja lógica de recursos (`PA-16`) y el tratamiento de los turnos ya asignados (`RP-07`) están pendientes de definición. El detalle operativo —quién autoriza el bloqueo, cómo se visualiza y cómo se libera— también queda abierto (`PA-01`).

### RN-08 — Sin sobreturnos en el MVP

El MVP no admite excepciones de sobreposición por urgencias. Si un profesional o un sillón está ocupado, el turno se rechaza aunque el caso sea urgente. La gestión de urgencias fuera de agenda queda fuera del MVP (`PA-02` resuelta).

### RN-09 — Precedencia de validación

Cuando el turno solicitado se solapa con un turno existente que comparte **profesional y sillón**, el sistema informa primero `SolapamientoProfesionalError`. Esta precedencia forma parte del comportamiento especificado y evita mensajes ambiguos.

## 4. Ejemplos

Todos los datos son sintéticos.

| # | Turno existente | Turno solicitado | Resultado |
|---|---|---|---|
| 1 | Dr. Pérez / Sillón 1, 2026-11-01 10:00–10:30 | Dr. Pérez / Sillón 2, 2026-11-01 10:15–10:45 | `SolapamientoProfesionalError` |
| 2 | Dr. Pérez / Sillón 1, 2026-11-01 10:00–10:30 | Dr. Ejemplo / Sillón 1, 2026-11-01 10:15–10:45 | `SolapamientoSillonError` |
| 3 | Dr. Pérez / Sillón 1, 2026-11-01 10:00–10:30 | Dr. Pérez / Sillón 1, 2026-11-01 10:15–10:45 | `SolapamientoProfesionalError` (RN-09) |
| 4 | Dr. Pérez / Sillón 1, 2026-11-01 10:00–10:30 | Dr. Pérez / Sillón 1, 2026-11-01 10:30–11:00 | Permitido: turnos contiguos |
| 5 | Dr. Pérez / Sillón 1, 2026-11-01 10:00–10:30 | Dr. Pérez / Sillón 1, 2026-11-02 10:00–10:30 | Permitido: otra fecha |
| 6 | Dr. Pérez / Sillón 1, 2026-11-01 10:00–10:30, cancelado | Dr. Pérez / Sillón 1, 2026-11-01 10:15–10:45 | Permitido: el turno cancelado no bloquea |
| 7 | Dr. Pérez / Sillón 1, 2026-11-01 10:15–10:30 | Dr. Pérez / Sillón 2, 2026-11-01 10:00–10:20 | `SolapamientoProfesionalError` |

## 5. Casos de borde

| Caso | Comportamiento esperado | Estado |
|---|---|---|
| Turnos contiguos | Permitidos | Definido (`RN-02`) |
| Solapamiento invertido | Rechazado | Definido (`RN-02`) |
| Misma franja en otra fecha | Permitido | Definido |
| Conflicto simultáneo de ambos recursos | Excepción de profesional primero | Definido (`RN-09`) |
| Turno cancelado | No bloquea | Definido (`RN-04`) |
| Duración cero o negativa | Se propone rechazar; criterio pendiente (`RP-01`) | Pendiente (`RP-01`) |
| Horario fuera de la franja de atención | Se propone rechazar; criterio pendiente (`RP-02`) | Pendiente (`RP-02`) |
| Turno que cruza medianoche | Definir tratamiento | Pendiente (`RP-05`) |
| Dos altas simultáneas del mismo recurso | Evitar doble reserva por concurrencia | Pendiente (`RP-06`) |
| Feriados o cierres de la clínica | Definir si bloquean la agenda | Pendiente (`RP-02`) |
| Bloqueo o inactivación con turnos activos | Definir si se reprograman, cancelan o se impide el bloqueo | Pendiente (`RP-07`) |

## 6. Reglas pendientes de definición

| ID | Regla pendiente | Impacto |
|---|---|---|
| **RP-01** | Validación de fechas pasadas, duración mínima y coherencia `inicio < fin`. | Integridad del turno |
| **RP-02** | Horarios de atención, duración estándar, feriados y cierres. | Disponibilidad real |
| **RP-03** | Reglas de reprogramación: ¿cancelar y crear, o modificar el turno? | Historial y trazabilidad |
| **RP-04** | Política de cancelación: plazos, motivos y efectos. | Operación y acuerdos con pacientes |
| **RP-05** | Zona horaria y turnos que cruzan medianoche. | Cálculo de intervalos |
| **RP-06** | Estrategia de concurrencia y transacciones para evitar doble reserva. | Consistencia bajo carga |
| **RP-07** | Bloqueo o inactivación de un recurso con turnos activos: reprogramar, cancelar o impedir el bloqueo. | Integridad de la agenda y continuidad de la atención |

## 7. Documentos relacionados

- [data-models.md](data-models.md) — entidades, campos e invariantes.
- [features.md](features.md) — funcionalidades que aplican estas reglas.
- [flows.md](flows.md) — secuencia de validaciones y transiciones.
- [decisions.md](decisions.md) — decisiones técnicas y pendientes.
- [open-questions.md](open-questions.md) — preguntas abiertas asociadas.
