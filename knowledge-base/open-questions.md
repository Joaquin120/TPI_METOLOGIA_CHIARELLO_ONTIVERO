# Preguntas Abiertas

Este documento centraliza la información que todavía no está definida. Cada pregunta tiene un identificador estable, un estado y el impacto que genera. Las decisiones técnicas pendientes se registran en [decisions.md](decisions.md) para evitar duplicación.

## 1. Convenciones

| Campo | Valores |
|---|---|
| **ID** | `PA-XX` |
| **Estado** | `Abierta`, `Resuelta`, `Diferida` |
| **Impacto** | `Alto`, `Medio`, `Bajo` |
| **Decisión MVP** | Acción o criterio adoptado mientras la pregunta no se resuelve |

## 2. Preguntas de negocio y producto

| ID | Tema | Pregunta | Estado | Impacto | Decisión / acción MVP |
|---|---|---|---|---|---|
| **PA-01** | Mantenimiento de sillón | ¿Cómo se gestiona un sillón fuera de servicio y qué ocurre con los turnos ya asignados? | Abierta | Medio | Se prevé bloquearlo mediante un turno de bloqueo o inactivando el recurso; el modelo y la operación siguen pendientes (`PA-15`, `PA-16`, `RP-07`). |
| **PA-02** | Sobreturnos y urgencias | ¿Se permite sobreponer turnos por urgencias? | Resuelta | Alto | No se permiten excepciones en el MVP. Se prioriza la coherencia física de los recursos (`RN-08`). |
| **PA-03** | Facturación AFIP/ARCA | ¿Cuál es el alcance de la facturación electrónica? | Abierta | Bajo | Fuera del MVP. Se evalúa como módulo futuro. |
| **PA-04** | Modelo de negocio del SaaS | ¿Cómo se cobra la plataforma a cada clínica y cómo es el onboarding? | Abierta | Alto | Sin definición. No condiciona el MVP funcional, pero sí la operación comercial. |
| **PA-05** | Portal del paciente | ¿El paciente reserva, cancela o solo confirma? ¿Requiere autenticación? | Abierta | Alto | No incluido en el MVP. La segunda etapa contempla confirmación por WhatsApp. |
| **PA-06** | Cancelación y reprogramación | ¿Qué plazos, motivos y efectos tiene la cancelación? ¿Cómo se reprograma? | Abierta | Alto | La cancelación básica está en el MVP; plazos y motivos están pendientes (`RP-04`). La reprogramación está prevista en el MVP (`F-09`), pero su mecanismo sigue pendiente de definición (`RP-03`); no se declara fuera de alcance. |
| **PA-07** | Métricas de éxito | ¿Qué métricas se van a medir y con qué objetivos? | Abierta | Medio | Sin métricas ni tableros definidos. |
| **PA-08** | Multi-sucursal | ¿Se necesita administrar varias sucursales bajo una misma clínica? | Abierta | Bajo | Fuera del MVP. Requiere revisar el modelo de tenancy. |
| **PA-09** | Cobros y medios de pago | ¿Se van a cobrar señas o pagos online? ¿Con qué proveedor? | Abierta | Medio | No comprometido. El discovery lo identifica como oportunidad de mercado. |
| **PA-10** | Horarios y duración | ¿Cuál es la duración estándar de un turno? ¿Cómo se definen franjas, feriados y cierres? | Abierta | Alto | Sin definición. Afecta la disponibilidad real y la agenda (`RP-02`, `DP-08`). |
| **PA-11** | Notificaciones | ¿Cuándo se envía cada recordatorio? ¿Qué plantillas y opt-in se usan? | Abierta | Medio | La segunda etapa incluye WhatsApp; momentos y plantillas pendientes (`DP-09`). |
| **PA-12** | Privacidad y retención | ¿Cuánto tiempo se conservan los datos y cómo se tratan los datos productivos? | Abierta | Medio | El MVP solo exige datos sintéticos en desarrollo y pruebas (`RN-06`). |
| **PA-13** | Estado inicial del turno | ¿El alta desde recepción crea el turno en `PENDIENTE` o en `CONFIRMADO`? | Abierta | Alto | La especificación vigente usa `CONFIRMADO`; el ciclo de vida contempla `PENDIENTE`. |
| **PA-14** | Lista de espera | ¿Cómo se prioriza y notifica a los pacientes en espera? | Abierta | Bajo | Segunda etapa. Sin reglas definidas. |
| **PA-15** | Modelo de turno de bloqueo | ¿Cómo se representa un bloqueo de sillón o de profesional? ¿Ocupa ambos recursos? | Abierta | Medio | `RN-07` lo menciona y [data-models.md](data-models.md) incluye una entidad propuesta; la definición sigue abierta. |
| **PA-16** | Baja lógica de recursos | ¿La baja de profesionales y sillones es inactivación o borrado lógico? ¿Qué ocurre con sus turnos futuros? | Abierta | Medio | `F-10` la menciona; se propone `activo` en `Profesional` y `DP-06` todavía no define el borrado. |

## 3. Resoluciones transversales del MVP

| ID | Decisión | Fundamento |
|---|---|---|
| `RN-02` | Los turnos contiguos son válidos. | El intervalo semiabierto refleja la operación real. |
| `RN-08` | La validación no admite excepciones por urgencia en el MVP. | Evita ambigüedad en la agenda inicial. |

> Estas filas referencian reglas ya definidas en [business-rules.md](business-rules.md); no son definiciones nuevas. `PA-02` está resuelta; `PA-01` sigue abierta en su detalle operativo (`PA-15`, `PA-16`, `RP-07`).

## 4. Preguntas técnicas derivadas

El detalle de cada una se encuentra en [decisions.md](decisions.md).

| ID | Tema | Pregunta asociada |
|---|---|---|
| `DP-01` | Stack backend | ¿Python/FastAPI es la definición final? ¿Node.js sigue vigente? |
| `DP-02` | Persistencia de producción | ¿Qué base de datos y ORM se usan? |
| `DP-03` | Aislamiento multi-tenant | ¿Base compartida, esquema por tenant u otra estrategia? |
| `DP-04` | Autenticación | ¿Cómo se autentican los usuarios y cómo se resuelve el tenant? |
| `DP-05` | Concurrencia | ¿Cómo se evita la doble reserva con altas simultáneas? |
| `DP-06` | Identificadores y auditoría | ¿UUID o Integer? ¿Qué se audita y cómo? |
| `DP-07` | Zona horaria | ¿Cómo se tratan turnos que cruzan medianoche? |
| `DP-08` | Horarios | ¿Cómo se modela la disponibilidad de profesionales y sillones? |
| `DP-09` | Notificaciones | ¿Qué proveedor de WhatsApp se usa? |
| `DP-10` | Despliegue | ¿Dónde se despliega y cómo se gestionan secretos? |
| `DP-11` | Módulos administrativos | ¿Qué alcance tienen pagos, AFIP y honorarios? |

## 5. Reglas de negocio pendientes (`RP-XX`)

El detalle normativo está en [business-rules.md](business-rules.md); esta tabla solo centraliza el índice para evitar duplicación.

| ID | Tema | Documento |
|---|---|---|
| `RP-01` | Validación de fechas pasadas, duración mínima y coherencia `inicio < fin`. | [business-rules.md](business-rules.md) |
| `RP-02` | Horarios de atención, duración estándar, feriados y cierres. | [business-rules.md](business-rules.md) |
| `RP-03` | Reglas de reprogramación: cancelar y crear, o modificar el turno. | [business-rules.md](business-rules.md) |
| `RP-04` | Política de cancelación: plazos, motivos y efectos. | [business-rules.md](business-rules.md) |
| `RP-05` | Zona horaria y turnos que cruzan medianoche. | [business-rules.md](business-rules.md) |
| `RP-06` | Estrategia de concurrencia y transacciones para evitar doble reserva. | [business-rules.md](business-rules.md) |
| `RP-07` | Bloqueo o inactivación de un recurso con turnos activos: reprogramar, cancelar o impedir el bloqueo. | [business-rules.md](business-rules.md) |

## 6. Prioridad de resolución

| Prioridad | Preguntas | Motivo |
|---|---|---|
| **Alta** | `PA-13`, `PA-10`, `PA-06`, `PA-05`, `PA-04`, `RP-07`, `DP-01`, `DP-02`, `DP-03`, `DP-04` | Afectan el alcance del MVP, el contrato de la API y la operación. |
| **Media** | `PA-01`, `PA-07`, `PA-09`, `PA-11`, `PA-12`, `PA-15`, `PA-16`, `DP-05`, `DP-06`, `DP-08`, `DP-09` | Afectan calidad, operación y segunda etapa. |
| **Baja** | `PA-03`, `PA-08`, `PA-14`, `DP-07`, `DP-10`, `DP-11` | Pueden resolverse después del MVP. |

## 7. Documentos relacionados

- [vision.md](vision.md) — alcance y etapas.
- [business-rules.md](business-rules.md) — reglas y pendientes `RP-XX`.
- [decisions.md](decisions.md) — decisiones técnicas y `DP-XX`.
- [features.md](features.md) — funcionalidades afectadas.
- [data-models.md](data-models.md) — entidades y campos pendientes.
