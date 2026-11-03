# Decisiones Arquitectónicas y Tecnológicas

Este documento registra las decisiones tomadas, su contexto y sus consecuencias. La arquitectura resultante se describe en [architecture.md](architecture.md). Las preguntas de negocio pendientes se centralizan en [open-questions.md](open-questions.md).

## 1. Contexto y criterios

El producto se construye bajo **Spec-Driven Development (SDD)** con OpenSpec. Las decisiones se evalúan con estos criterios:

- Que el dominio de agenda pueda probarse sin infraestructura.
- Que el aislamiento multi-tenant sea explícito.
- Que la solución sea adoptable por consultorios chicos y clínicas multi-box.
- Que el stack permita iterar rápido sin comprometer la consistencia de las reservas.
- Que las decisiones puedan revisarse cuando exista nueva información.

## 2. Decisiones confirmadas

| ID | Decisión | Contexto | Consecuencias |
|---|---|---|---|
| **D-01** | SaaS web-first y multi-tenant. | El producto se ofrece a varias clínicas desde una misma plataforma. | Cada entidad y consulta incorpora `tenant_id`; el onboarding y la facturación del SaaS quedan pendientes. |
| **D-02** | Arquitectura en capas con monolito modular. | Se necesita separar dominio, API y persistencia sin complejidad distribuida. | Un único despliegue con módulos delimitados; la estructura física definitiva depende de `DP-01` y `DP-02`. |
| **D-03** | Python 3.11+ como lenguaje vigente del núcleo implementado. | Es el lenguaje del dominio y de la guía de estilo del proyecto. | Tipado estático, PEP 8 y excepciones de dominio explícitas. La confirmación del stack completo y el descarte de Node.js quedan en `DP-01`. |
| **D-04** | SQLite para desarrollo y pruebas. | Se necesita una base liviana y reproducible para validar el dominio. | No se usa como decisión de producción; la base definitiva está pendiente (`DP-02`). |
| **D-05** | Configuración de la aplicación por variables de entorno (`.env`). | La aplicación requiere configuración externalizada y no deben existir secretos en el repositorio. | La configuración de la app se externaliza. La dirección arquitectónica es persistir los parámetros por tenant en el modelo de datos, pero el modelo concreto continúa pendiente (`PA-04`, `DP-03`, `DP-10`). |
| **D-06** | Excepciones de dominio explícitas. | El rechazo por solapamiento debe ser identificable y no un error genérico. | `SolapamientoProfesionalError` y `SolapamientoSillonError` forman parte del contrato del dominio. |
| **D-07** | Intervalos semiabiertos `[inicio, fin)`. | Se necesitan turnos contiguos sin falsos positivos. | La comparación usa `inicio_a < fin_b AND fin_a > inicio_b`; el límite exacto no es conflicto. |
| **D-08** | SDD con OpenSpec y reglas de `AGENTS.md`. | El proyecto exige especificar antes de implementar y mantener trazabilidad. | Cada cambio atraviesa `propose → apply → verify → archive`; las reglas duras de privacidad y doble validación son obligatorias. |
| **D-09** | Pruebas unitarias obligatorias sobre las reglas de agenda. | La corrección del doble candado es el núcleo del producto. | La suite debe cubrir camino feliz, conflictos por profesional, conflictos por sillón, contiguos y casos de borde. |
| **D-10** | API REST/JSON como interfaz del MVP. | La plataforma es web-first y necesita un contrato claro entre cliente y servidor. | Los endpoints se documentan en [features.md](features.md); el contrato definitivo y los códigos HTTP están pendientes. |

### 2.1. Justificación ampliada de las decisiones centrales

**D-01 — Multi-tenant.** La plataforma no se instala por clínica: varias clínicas comparten la misma aplicación. Por eso el tenant no es un detalle de despliegue, sino una dimensión del modelo de datos y de cada consulta. La estrategia física de aislamiento todavía no está decidida (`DP-03`).

**D-02 — Monolito modular.** La agenda tiene reglas complejas pero un volumen inicial acotado. Un monolito modular permite mantener el dominio cohesivo, probar las reglas sin red y evitar la complejidad operativa de microservicios prematuros.

**D-06 — Excepciones de dominio.** Un conflicto de agenda no es un error técnico: es una regla de negocio. Modelarlo con excepciones específicas permite que la API, la interfaz y las pruebas distingan si el problema es el profesional o el sillón.

**D-07 — Intervalos semiabiertos.** Si se usaran intervalos cerrados, un turno de 10:00 a 10:30 y otro de 10:30 a 11:00 se considerarían solapados. El intervalo semiabierto refleja la operación real: el sillón se libera a las 10:30 y puede recibir al siguiente paciente.

## 3. Decisiones pendientes

| ID | Decisión pendiente | Impacto | Pregunta asociada |
|---|---|---|---|
| **DP-01** | Stack backend definitivo: Python/FastAPI u otra alternativa; confirmar si Node.js sigue vigente. | Framework, estructura y despliegue. | — |
| **DP-02** | Base de datos y ORM/migraciones de producción. | Persistencia, transacciones y despliegue. | — |
| **DP-03** | Estrategia de aislamiento multi-tenant. | Modelo físico y seguridad. | `PA-04`, `PA-08` |
| **DP-04** | Autenticación, autorización y sesiones. | Acceso por rol y aislamiento. | `PA-05` |
| **DP-05** | Concurrencia y transacciones para evitar doble reserva. | Consistencia bajo altas simultáneas. | `RP-06` |
| **DP-06** | Tipo de identificadores, timestamps, auditoría y borrado lógico. | Diseño de tablas y migraciones. | `PA-16` |
| **DP-07** | Zona horaria y tratamiento de turnos que cruzan medianoche. | Cálculo de intervalos. | `RP-05` |
| **DP-08** | Modelo de disponibilidad y horarios de atención; relación con el turno de bloqueo. | Disponibilidad real y agenda. | `PA-10`, `PA-15` |
| **DP-09** | Proveedor de notificaciones y condiciones de WhatsApp. | Costos, cumplimiento y arquitectura de mensajería. | `PA-11` |
| **DP-10** | Infraestructura de despliegue y gestión de secretos. | Operación y seguridad. | — |
| **DP-11** | Alcance de pagos, AFIP y otros módulos administrativos. | Roadmap y alcance futuro. | `PA-03`, `PA-09` |

## 4. Supuestos

| ID | Supuesto | Si no se cumple |
|---|---|---|
| **S-01** | La operación principal es en Argentina y en horario local. | Habría que definir zonas horarias y normativa adicional. |
| **S-02** | La clínica tiene conectividad web durante el horario de atención. | La agenda y las notificaciones requerirían un modo offline o contingencia. |
| **S-03** | WhatsApp es el canal prioritario de recordatorios. | Habría que evaluar email, SMS u otro canal. |
| **S-04** | Los datos de desarrollo y demostración son sintéticos. | Se incumpliría la regla de privacidad `RN-06`. |
| **S-05** | El consultorio objetivo tiene entre 1 y 3 sillones, o es una clínica multi-box acotada. | El modelo de agenda y la experiencia podrían necesitar otro diseño. |

## 5. Estrategia de pruebas

### 5.1. Niveles

| Nivel | Alcance | Criterio |
|---|---|---|
| **Unitario** | Reglas de dominio: solapamiento, contiguos, estados, liberación por cancelación. | Debe ejecutarse sin base de datos ni HTTP. |
| **Integración** | API, repositorios y persistencia. | Pendiente de definición (`DP-02`). |
| **Extremo a extremo** | Flujos completos de recepción. | Pendiente de definición. |

### 5.2. Casos mínimos del núcleo

| Caso | Resultado esperado |
|---|---|
| Alta sin conflicto | Turno registrado |
| Conflicto de profesional con otro sillón | `SolapamientoProfesionalError` |
| Conflicto de sillón con otro profesional | `SolapamientoSillonError` |
| Conflicto de ambos recursos | `SolapamientoProfesionalError` por `RN-09` |
| Turnos contiguos | Permitidos |
| Solapamiento invertido | Rechazado |
| Misma franja en otra fecha | Permitido |
| Turno cancelado | No bloquea |
| Bloqueo de sillón | Pendiente (`PA-15`, `PA-16`, `RP-07`) |

### 5.3. Criterio de aceptación

- La suite debe quedar en verde antes de cerrar un cambio.
- La cobertura objetivo es completa sobre los casos de solapamiento y transiciones de estado.
- Las pruebas usan exclusivamente datos sintéticos.
- Los comandos de referencia son `pytest` y `pytest --cov=src`.

## 6. Documentos relacionados

- [architecture.md](architecture.md) — cómo se materializan las decisiones.
- [business-rules.md](business-rules.md) — reglas que las pruebas deben verificar.
- [data-models.md](data-models.md) — modelo de datos objetivo.
- [open-questions.md](open-questions.md) — preguntas de negocio y producto.
