# Actores y Permisos

Este documento define quién usa el sistema, qué puede hacer y qué restricciones tiene. Las funcionalidades concretas se detallan en [features.md](features.md) y los flujos operativos en [flows.md](flows.md).

## 1. Actores del sistema

| Actor | Tipo | Descripción |
|---|---|---|
| **Administrador de Clínica** | Interno | Responsable de configurar la clínica, sus profesionales, sillones y horarios. |
| **Recepcionista** | Interno | Responsable de la operación diaria de la agenda: alta, confirmación, reprogramación y cancelación de turnos. |
| **Profesional** | Interno | Odontólogo que consulta su agenda individual y el estado de sus turnos. |
| **Paciente** | Externo | Persona que recibe la atención y, en etapas posteriores, recibe recordatorios y confirma o cancela su asistencia. |
| **Sistema** | Automático | Ejecuta validaciones, transiciones de estado y notificaciones programadas. |

## 2. Responsabilidades por rol

### 2.1. Administrador de Clínica

- Configurar los profesionales de la clínica.
- Configurar los sillones/boxes y su equipamiento.
- Definir los horarios de atención.
- Gestionar la configuración general del tenant; el alcance y los parámetros están pendientes (`PA-04`).
- Autorizar bloqueos de sillón por mantenimiento; el mecanismo está pendiente (`PA-15`, `PA-16`).
- Supervisar la operación sin necesariamente operar la agenda diaria.

### 2.2. Recepcionista

- Crear turnos para cualquier profesional y cualquier sillón de la clínica.
- Confirmar turnos pendientes.
- Reprogramar turnos cuando sea necesario.
- Cancelar turnos y liberar los recursos.
- Consultar la agenda general y la de cada profesional.
- Detectar el conflicto de agenda informado por el sistema y elegir otro horario, profesional o sillón. No puede forzar la reserva ni omitir la doble validación (`RN-01`, `RN-08`).

### 2.3. Profesional

- Consultar su agenda individual.
- Consultar el estado de sus turnos.
- No administra recursos ni la agenda de otros profesionales.
- La carga de evolución clínica u odontograma queda fuera del MVP y se evalúa como futuro.

### 2.4. Paciente

- Recibir la atención en el turno reservado.
- Recibir recordatorios por WhatsApp en la segunda etapa.
- Confirmar o cancelar su asistencia desde el mensaje, cuando esa funcionalidad esté disponible.
- El portal de autoservicio y la reserva online están pendientes de definición (`PA-05`).

### 2.5. Sistema

- Validar la disponibilidad de profesional y sillón antes de registrar un turno.
- Aplicar las transiciones de estado permitidas.
- Liberar recursos cuando un turno se cancela.
- Generar eventos de notificación en la segunda etapa.
- Registrar y comunicar errores de dominio de forma explícita.

## 3. Matriz de permisos

Valores:

- **SÍ:** permitido de forma explícita.
- **NO:** no permitido.
- **PARCIAL:** permitido solo dentro de su ámbito (por ejemplo, agenda propia).
- **PENDIENTE:** no definido todavía.

| Recurso / Acción | Administrador | Recepcionista | Profesional | Paciente |
|---|---|---|---|---|
| Consultar profesionales | SÍ | SÍ | PENDIENTE | NO |
| Consultar sillones/boxes | SÍ | SÍ | PENDIENTE | NO |
| Gestionar profesionales | SÍ | NO | NO | NO |
| Gestionar sillones/boxes | SÍ | NO | NO | NO |
| Configurar horarios de atención | SÍ | PENDIENTE | NO | NO |
| Ver agenda general | PENDIENTE | SÍ | PARCIAL (solo propia) | NO |
| Ver agenda propia | PENDIENTE | SÍ | SÍ | PENDIENTE |
| Crear turno | PENDIENTE | SÍ | NO | PENDIENTE |
| Confirmar turno | PENDIENTE | SÍ | NO | PENDIENTE |
| Reprogramar turno | PENDIENTE | SÍ | NO | PENDIENTE |
| Cancelar turno | PENDIENTE | SÍ | NO | PENDIENTE |
| Completar turno | PENDIENTE | PENDIENTE | PENDIENTE | NO |
| Consultar datos de pacientes | PENDIENTE | SÍ | PENDIENTE | NO |
| Gestionar pacientes | PENDIENTE | PENDIENTE | NO | NO |
| Gestionar bloqueo de sillón | SÍ | PENDIENTE | NO | NO |
| Configurar el tenant (aislamiento y recursos) | SÍ | NO | NO | NO |
| Configurar parámetros operativos del tenant | PENDIENTE | NO | NO | NO |
| Recibir notificaciones | NO | PENDIENTE | PENDIENTE | SÍ (segunda etapa) |

> La recepcionista puede ver la agenda general porque gestiona turnos de cualquier profesional y sillón. El alcance exacto de esa vista se define en la segunda etapa, junto con la agenda matricial.
>
> El alta y la consulta de pacientes están previstas en el MVP (`F-11`), pero el rol que las ejecuta no está confirmado. Por eso la matriz mantiene **Gestionar pacientes** como `PENDIENTE` y no se presenta el permiso como otorgado.

## 4. Superficies de acceso

| Superficie | Actores | Etapa | Observaciones |
|---|---|---|---|
| Aplicación web | Administrador, Recepcionista, Profesional | MVP | El producto es web-first. |
| API REST/JSON | Clientes internos | MVP | Contrato documentado en [features.md](features.md). |
| Portal del paciente | Paciente | Pendiente | No definido (`PA-05`). |
| Mensajería WhatsApp | Paciente | Segunda etapa | Recordatorios y acciones de confirmación/cancelación. |

No se definen rutas, pantallas ni flujos de navegación hasta que exista una especificación de interfaz.

## 5. Restricciones

- **Aislamiento por tenant:** ningún actor puede ver ni operar datos de otra clínica (`RN-05`).
- **Agenda propia:** el profesional solo accede a sus propios turnos.
- **Doble validación:** ningún rol puede omitir la validación de profesional y sillón (`RN-01`).
- **Sin sobreturnos:** la recepción no puede forzar una sobreposición en el MVP (`RN-08`).
- **Privacidad:** los datos de ejemplo y pruebas son sintéticos (`RN-06`).
- **Trazabilidad:** las acciones que cambian el estado de un turno deben quedar asociadas a un usuario y un momento; el modelo de auditoría está pendiente (`DP-06`).

## 6. Casos de uso por actor

| Actor | Caso de uso | Resultado esperado |
|---|---|---|
| Administrador | Alta de un profesional | El profesional queda disponible para asignar turnos. |
| Administrador | Alta de un sillón | El sillón queda disponible para asignar turnos. |
| Administrador | Bloqueo de un sillón | El recurso no se ofrece durante el intervalo bloqueado; el mecanismo está pendiente y la clasificación en el MVP es una propuesta (`PA-15`, `PA-16`). |
| Recepcionista | Alta de un turno | El turno se registra si ambos recursos están libres. |
| Recepcionista | Alta de un turno con conflicto | El sistema rechaza la operación con la excepción correspondiente. |
| Recepcionista | Cancelación de un turno | El turno pasa a `CANCELADO` y libera ambos recursos. |
| Recepcionista | Reprogramación | El turno anterior se libera y se registra el nuevo horario; el mecanismo está pendiente (`RP-03`). |
| Profesional | Consulta de agenda | Ve únicamente sus turnos y estados. |
| Paciente | Recepción de recordatorio | Recibe el aviso y puede confirmar o cancelar en la segunda etapa. |

## 7. Permisos pendientes de definición

| Tema | Pregunta | Impacto |
|---|---|---|
| Alta de turnos por Administrador | ¿El administrador opera la agenda o solo configura? | Matriz RBAC |
| Finalización de turnos | ¿Quién marca `COMPLETADO`: recepción o profesional? | Flujo operativo |
| Gestión de pacientes | ¿Quién crea y edita pacientes? | Módulo de pacientes; la matriz mantiene el permiso como `PENDIENTE`. |
| Portal del paciente | ¿El paciente reserva, cancela o solo confirma? | Alcance y autenticación |
| Multi-rol | ¿Un usuario puede ser administrador y profesional a la vez? | Modelo de usuarios |
| Auditoría | ¿Qué acciones requieren registro de usuario y fecha? | Trazabilidad |

## 8. Documentos relacionados

- [features.md](features.md) — funcionalidades por rol.
- [flows.md](flows.md) — pasos de cada operación.
- [business-rules.md](business-rules.md) — restricciones normativas.
- [architecture.md](architecture.md) — aislamiento y seguridad.
- [open-questions.md](open-questions.md) — definiciones pendientes.
