# Descripción del Sistema

## 1. Qué es el sistema

Es una plataforma SaaS web-first y multi-tenant para la gestión de turnos odontológicos. Permite administrar profesionales, sillones/boxes, pacientes y la agenda de atención, garantizando que ningún turno se registre si el profesional o el sillón asignado ya están ocupados en el mismo intervalo.

El sistema está pensado para consultorios y clínicas que necesitan una agenda compartida por varios recursos físicos, no solo por profesionales. Su núcleo funcional es el **motor de validación bidireccional** descrito en [business-rules.md](business-rules.md).

## 2. Problema que resuelve

La agenda odontológica requiere dos recursos simultáneos: el profesional y el sillón/box equipado. Los turneros que solo controlan al profesional permiten dobles reservas físicas; los sistemas que sí controlan gabinetes suelen ser costosos, complejos o poco adaptados al mercado argentino.

El sistema resuelve ese problema con una agenda única que:

- valida ambos recursos en el momento del alta;
- permite turnos contiguos sin falsos positivos;
- libera los recursos cuando un turno se cancela;
- contempla una vista de agenda por profesional y por sillón en la segunda etapa.

El contexto de mercado y la propuesta de valor se desarrollan en [vision.md](vision.md).

## 3. Módulos principales

| Módulo | Propósito | Capacidades principales | Referencia |
|---|---|---|---|
| **Agenda y Turnos** | Gestionar la reserva y el ciclo de vida de los turnos. | Alta, consulta, confirmación, cancelación, reprogramación y cambio de estado. | `F-01`, `F-02`, `F-03`, `F-09` |
| **Recursos** | Administrar los recursos que hacen posible la atención. | Profesionales, sillones/boxes, horarios y bloqueos por mantenimiento. | `F-04`, `F-05`, `F-10`, `F-12` |
| **Pacientes** | Mantener los datos mínimos del paciente asociado al turno. | Alta y consulta de pacientes con datos de contacto. | `F-11` |
| **Notificaciones** | Reducir el ausentismo mediante avisos oportunos. | Eventos internos de agenda; recordatorios y confirmación por WhatsApp (segunda etapa). | `F-07` |
| **Administración y Tenant** | Configurar y aislar la operación de cada clínica. | Aislamiento por tenant y configuración básica de recursos; usuarios, parámetros y facturación pendientes. | Parcial |

## 4. Capacidades por módulo

### 4.1. Agenda y Turnos

- Registrar un turno indicando paciente, profesional, sillón, fecha y horario.
- Validar de forma simultánea e independiente la disponibilidad de profesional y sillón.
- Rechazar el alta cuando existe solapamiento, con una excepción de dominio específica.
- Permitir turnos contiguos en el límite exacto del intervalo.
- Consultar turnos con filtros por profesional, sillón y fecha.
- Cambiar el estado del turno según las transiciones válidas.
- Cancelar un turno y liberar de inmediato ambos recursos.
- Reprogramar un turno (detalle de flujo y endpoint pendiente de definición).
- Visualizar la agenda por profesional y por sillón en la segunda etapa.

### 4.2. Recursos

- Listar profesionales disponibles.
- Listar sillones/boxes disponibles.
- Configurar profesionales, sillones y horarios de atención desde el rol administrador.
- Inactivar un sillón o registrar un bloqueo por mantenimiento (mecanismo pendiente, `PA-15`, `PA-16`).
- Consultar la ocupación de un recurso en una fecha determinada (alcance pendiente de definición).

### 4.3. Pacientes

- Registrar los datos mínimos del paciente: identificación, nombre y teléfono.
- Asociar el paciente a uno o más turnos.
- Consultar los turnos de un paciente (alcance pendiente de definición).

### 4.4. Notificaciones

El módulo distingue dos capacidades que no deben confundirse:

- **Generar eventos internos:** registrar que ocurrió un hecho de agenda —por ejemplo, el alta o la confirmación de un turno— para uso interno o como insumo de etapas posteriores. Esta capacidad no implica el envío de mensajes.
- **Enviar notificaciones automáticas:** recordatorios por WhatsApp y confirmación o cancelación por parte del paciente. Esta capacidad pertenece a la segunda etapa y está fuera del MVP.
- Definir momentos, plantillas, opt-in y proveedor: pendiente de definición (`PA-11`, `DP-09`).

La generación de eventos internos no incorpora las notificaciones automáticas al MVP ni contradice los límites de la sección 5.

### 4.5. Administración y Tenant

**Definido en el producto:**

- Aislar la información de cada clínica mediante `tenant_id`.
- Configurar profesionales, sillones y horarios de atención (endpoints pendientes, `F-10`).

**Pendiente de definición:**

- Los parámetros operativos configurables por tenant (`PA-04`).
- Gestionar usuarios y roles; el modelo de usuarios y la autenticación están pendientes (`DP-04`).
- El onboarding y la facturación del SaaS (`PA-04`).

## 5. Límites del MVP

El MVP se concentra en el núcleo operativo de la agenda:

- Entidades base y relaciones entre profesional, sillón, paciente y turno.
- Doble validación de disponibilidad.
- Ciclo de estados y liberación de recursos por cancelación.
- Turnos contiguos.
- Alta y consulta de turnos.
- Administración básica de profesionales, sillones y horarios.
- Bloqueo de sillón por mantenimiento (clasificación propuesta, pendiente de validación; el mecanismo no está definido, ver `PA-15`, `PA-16`).
- Política estricta sin sobreturnos.

Quedan fuera del MVP las notificaciones automáticas —el MVP no envía mensajes, aunque el sistema pueda registrar eventos internos de agenda—, la agenda matricial, la lista de espera, el odontograma, la facturación fiscal, los honorarios, el inventario y la operación multi-sucursal. El detalle de etapas está en [vision.md](vision.md) y el catálogo funcional en [features.md](features.md).

## 6. Integraciones previstas

| Integración | Etapa | Propósito | Estado |
|---|---|---|---|
| API REST/JSON | MVP | Exponer las operaciones de agenda y recursos. | Definida como estilo de interfaz |
| WhatsApp | Segunda etapa | Recordatorios y confirmación/cancelación por parte del paciente. | Proveedor y condiciones pendientes |
| AFIP/ARCA | Futuro | Facturación electrónica. | Fuera del MVP; alcance pendiente |
| Medios de pago locales | No comprometido | Cobros o señas online. | Oportunidad de mercado; pendiente de definición |

## 7. Modelo de operación multi-tenant

Cada clínica o consultorio opera como un **tenant** aislado. Esto implica:

- Toda entidad de negocio pertenece a un tenant.
- Las consultas y validaciones deben ejecutarse dentro del tenant de la sesión.
- Un turno no puede referenciar profesionales, sillones o pacientes de otro tenant.
- La estrategia física de aislamiento (base compartida, esquema separado u otra) está pendiente de definición.

El modelo se desarrolla en [architecture.md](architecture.md) y [data-models.md](data-models.md).

## 8. Mapa de la Knowledge Base

| Archivo | Cuándo leerlo |
|---|---|
| [vision.md](vision.md) | Entender el problema, la propuesta de valor y el alcance por etapas. |
| [description.md](description.md) | Comprender qué es el sistema y cómo se compone. |
| [actors.md](actors.md) | Consultar roles, permisos y restricciones. |
| [architecture.md](architecture.md) | Entender capas, módulos, tenancy e integraciones. |
| [business-rules.md](business-rules.md) | Aplicar las reglas del dominio. |
| [data-models.md](data-models.md) | Modelar entidades, relaciones e invariantes. |
| [decisions.md](decisions.md) | Conocer decisiones técnicas, supuestos y pendientes. |
| [features.md](features.md) | Consultar funcionalidades, endpoints y criterios de aceptación. |
| [flows.md](flows.md) | Seguir un flujo paso a paso. |
| [open-questions.md](open-questions.md) | Revisar qué falta definir y su impacto. |

## 9. Documentos relacionados

- [vision.md](vision.md) — propósito y alcance.
- [actors.md](actors.md) — quién usa el sistema.
- [features.md](features.md) — detalle funcional.
- [flows.md](flows.md) — comportamiento paso a paso.
- [open-questions.md](open-questions.md) — definiciones pendientes.
