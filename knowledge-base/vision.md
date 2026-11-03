# Visión del Producto

## 1. Propósito

El sistema es una plataforma **SaaS web-first y multi-tenant** para la gestión de clínicas y consultorios odontológicos en Argentina. Su objetivo es centralizar la operación diaria —agenda, profesionales, sillones/boxes y pacientes— sobre una regla central: **ningún turno puede existir si no están disponibles, al mismo tiempo, el profesional que atiende y el sillón/box donde se realiza la atención**.

La visión no es construir un turnero médico genérico, sino un sistema específicamente dental que trate al sillón como un recurso finito de primera clase, con la misma jerarquía que el profesional.

## 2. Contexto y problema

### 2.1. El problema del doble recurso

En la mayoría de los turneros médicos la agenda se organiza únicamente alrededor del profesional. En odontología eso es insuficiente: cada atención requiere un profesional **y** un sillón/box equipado. Si el sistema solo controla al odontólogo, la recepción puede asignar dos pacientes al mismo sillón en el mismo horario, o dejar un sillón inutilizado mientras el profesional queda libre.

El relevamiento de mercado identificó que:

- Los turneros tradicionales no modelan el sillón/box como recurso asignable.
- Las soluciones de nicho que sí lo contemplan presentan fricciones para el mercado argentino: cotizaciones en divisa extranjera, venta consultiva obligatoria y canales de contacto poco ágiles (email/SMS) en lugar de mensajería instantánea.
- El consultorio chico y mediano suele quedar desatendido por plataformas sobredimensionadas para sanatorios.

### 2.2. Fricciones del mercado argentino

El discovery relevó los siguientes vacíos frecuentes:

- Precios y cotizaciones en moneda extranjera.
- Procesos comerciales opacos, con demos obligatorias para conocer condiciones.
- Falta de conexión nativa con medios de pago locales y con la normativa fiscal.
- Uso de canales de recordatorio de baja apertura en comparación con WhatsApp.
- Dificultad de adopción en consultorios de 1 a 3 sillones.

Estas fricciones son **contexto de mercado**, no funcionalidades comprometidas del MVP. El alcance concreto de pagos, facturación y multi-sucursal se define en [open-questions.md](open-questions.md).

### 2.3. Consecuencias del problema

- Doble reserva del mismo sillón o del mismo profesional.
- Ausentismo elevado por falta de recordatorios oportunos.
- Capacidad ociosa: sillones libres mientras hay pacientes esperando.
- Errores operativos en recepción al reprogramar o cancelar.
- Dificultad para saber, en un vistazo, qué recurso está ocupado y cuál está libre.

## 3. Propuesta de valor

| Problema | Respuesta del producto |
|---|---|
| El turnero solo controla al profesional | Validación simultánea e independiente de profesional y sillón/box |
| Agenda dispersa en planillas o sistemas separados | Agenda única multi-profesional y multi-sillón |
| Turnos consecutivos rechazados por error | Intervalos semiabiertos `[inicio, fin)` que permiten turnos contiguos |
| Ausentismo por falta de aviso | Recordatorios por WhatsApp en una etapa posterior del roadmap |
| Conflictos detectados tarde | Rechazo explícito en el momento del alta, con excepción de dominio identificable |
| Herramientas pensadas para grandes sanatorios | Producto orientado a consultorios de 1 a 3 sillones y clínicas multi-box |

## 4. Diferenciador core

El diferenciador es el **motor determinístico de doble candado**:

1. Antes de registrar un turno, el sistema verifica la disponibilidad del **profesional**.
2. De forma independiente, verifica la disponibilidad del **sillón/box**.
3. Ambas validaciones se aplican sobre el intervalo semiabierto `[inicio, fin)`, de modo que un turno que termina a las 10:30 y otro que comienza a las 10:30 son contiguos y válidos.
4. Si existe conflicto, el alta se rechaza con una excepción de dominio específica: `SolapamientoProfesionalError` o `SolapamientoSillonError`.
5. Un turno cancelado deja de bloquear ambos recursos.

El comportamiento normativo se desarrolla en [business-rules.md](business-rules.md) y su implementación objetivo en [architecture.md](architecture.md).

## 5. Objetivos por actor

| Actor | Objetivo principal |
|---|---|
| **Administrador de Clínica** | Configurar profesionales, sillones y horarios de atención; mantener la coherencia operativa del tenant. |
| **Recepcionista** | Crear, confirmar, reprogramar y cancelar turnos de cualquier profesional y sillón sin generar conflictos. |
| **Profesional** | Consultar su agenda individual y el estado de sus turnos. |
| **Paciente** | Recibir la atención en el horario reservado y, en etapas posteriores, recibir recordatorios y confirmar o cancelar su asistencia. |
| **Sistema** | Ejecutar validaciones, transiciones de estado y, cuando corresponda, notificaciones automáticas. |

El detalle de permisos y límites por rol está en [actors.md](actors.md).

## 6. Segmentos objetivo

| Segmento | Necesidad principal |
|---|---|
| **Consultorio de 1 a 3 sillones** | Agenda simple, bajo costo de adopción y control de doble recurso sin complejidad de sanatorio. |
| **Clínica multi-box** | Coordinación de varios profesionales y sillones en una agenda común, con visibilidad por recurso. |
| **Cadena o multi-sucursal** | Fuera del MVP; requiere definición de modelo de tenancy y administración centralizada. |

## 7. Alcance por etapas

La siguiente tabla ordena las capacidades del producto. La etapa indica **cuándo se espera construir**, no el estado actual del código.

| Etapa | Capacidades | Origen |
|---|---|---|
| **MVP** | Entidades base (`Profesional`, `Sillón`, `Paciente`, `Turno`); motor de doble candado; ciclo de estados; turnos contiguos; alta y consulta de turnos; administración de profesionales, sillones y horarios; bloqueo de sillón (propuesta pendiente de validación); política sin sobreturnos. | Discovery (MVP nuclear), KB actual, OpenSpec |
| **Segunda etapa** | Notificaciones y recordatorios por WhatsApp; agenda matricial por profesional y sillón; lista de espera y reasignación ante cancelaciones. | Discovery (segundo release) |
| **Futuro** | Odontograma y ficha periodontal; facturación electrónica/AFIP; liquidación de honorarios; control de inventario de insumos; multi-sucursal. | Discovery (etapas posteriores) |

> El bloqueo de sillón se propone para el MVP, pero el Discovery no lo enumera explícitamente y su clasificación sigue pendiente de validación. Su modelo y operación también están pendientes (`PA-15`, `PA-16`, `RP-07`).

## 8. Fuera de alcance del MVP

- Odontograma 3D o ficha periodontal interactiva.
- Integración fiscal directa con AFIP/ARCA.
- Liquidación de honorarios por profesional o práctica.
- Control de inventario de insumos dentales.
- Gestión multi-sucursal con administración centralizada.
- Cobros o señas online (el discovery lo menciona como oportunidad de mercado; no está definido como requisito).
- Portal de autoservicio para pacientes (reserva online): pendiente de definición.

## 9. Supuestos

- La operación principal ocurre en Argentina y en horario local.
- La clínica dispone de conectividad web durante su horario de atención.
- WhatsApp es el canal prioritario para recordatorios en la segunda etapa.
- El producto es multi-tenant: cada clínica o consultorio opera como un tenant aislado.
- Los datos usados en desarrollo, pruebas y demostraciones son sintéticos o anonimizados.
- El modelo de negocio, el precio y el onboarding autoservicio son oportunidades identificadas, pero **no están definidos**.

## 10. Métricas de éxito (pendiente de definición)

| Métrica | Por qué importa | Estado |
|---|---|---|
| Tasa de ausentismo (no-show) | Mide el impacto de los recordatorios | Pendiente de definición |
| Ocupación de sillones | Mide el aprovechamiento de la capacidad física | Pendiente de definición |
| Conflictos de agenda evitados | Mide el valor del doble candado | Pendiente de definición |
| Tiempo de alta de un turno | Mide la eficiencia de recepción | Pendiente de definición |
| Adopción de recordatorios | Mide la penetración de la segunda etapa | Pendiente de definición |

No se definen valores objetivo ni tableros hasta que el equipo acuerde la métrica y su forma de medición.

## 11. Documentos relacionados

- [description.md](description.md) — qué es el sistema y cómo se compone.
- [actors.md](actors.md) — roles, permisos y restricciones.
- [features.md](features.md) — catálogo de funcionalidades por etapa.
- [business-rules.md](business-rules.md) — reglas del dominio.
- [open-questions.md](open-questions.md) — información pendiente de definición.
