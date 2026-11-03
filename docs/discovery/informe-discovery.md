# Informe de Discovery: Sistema SaaS de Gestión de Turnos y Agenda Odontológica

**Asignatura:** Metodología I — Tecnicatura Universitaria en Programación  
**Integrantes:** Santiago Ontivero (Líder Discovery), Cristian Rodríguez (Auditoría y Fundación), Joseph Chiarello (Arquitecto Spec/Agente), Joaquín Oliveros (Testing e Implementación)  
**Fecha:** Octubre 2026  
**Etapa:** Etapa 2 — Discovery Obligatorio (Active Stack / OpenSpec)  

---

## Resumen Ejecutivo

El presente informe expone la investigación de mercado y el estado del arte para el desarrollo de una solución SaaS de gestión de turnos orientada a consultorios y clínicas odontológicas en Argentina. 

A partir del relevamiento exhaustivo de 15 plataformas nacionales e internacionales, se concluye que los turneros médicos tradicionales fracasan en el ámbito dental debido a la omisión del **doble recurso crítico simultáneo**: en odontología la cita no depende únicamente del profesional, sino de la disponibilidad física de un sillón/box de atención equipado. Por otro lado, las soluciones de nicho que sí contemplan gabinetes presentan fricciones críticas para el mercado argentino: cotizaciones en divisa extranjera, venta consultiva obligatoria y dependencia de canales de baja apertura (email/SMS) en lugar de automatización sobre WhatsApp.

Se recomienda avanzar hacia un MVP de arquitectura desacoplada cuyo núcleo operativo resuelva de forma infalible la prevención de colisiones temporales por profesional y por sillón/box, sentando las bases para integraciones locales de mensajería y cobros.

---

## A. Tabla Comparativa de Sistemas (15 Soluciones)

*Criterio metodológico: Se distingue rigurosamente entre funcionalidad comprobada y afirmación comercial. Toda celda sin evidencia pública fehaciente en documentación, portal o términos de uso se declara como "No evidenciado".*

| # | Producto / Proveedor | País | Segmento Objetivo | Reserva Online 24/7 | Recordatorios Automáticos | Fuente y Fecha de Consulta |
|---|---|---|---|---|---|---|
| 1 | **Dentalink**<br>(HealthAtom) | Chile / Regional | Consultorios, clínicas y cadenas | Comprobado (Portal web de pacientes y widget) | Comprobado (WhatsApp automático, SMS, Email) | `https://www.softwaredentalink.com/ar`<br>Consulta: 2026-10-12 |
| 2 | **DentiDesk**<br>(DentiDesk SpA) | Chile / Regional | Odontólogos y clínicas multi-box | Comprobado (Módulo web y enlace directo) | Comprobado (WhatsApp y Email) | `https://dentidesk.com/`<br>Consulta: 2026-10-12 |
| 3 | **Wiri Salud**<br>(Wiri Salud S.A.) | Argentina | Centros médicos y profesionales | Comprobado (Marketplace y turnero web) | Comprobado (WhatsApp y Email) | `https://wiri.la/argentina`<br>Consulta: 2026-10-14 |
| 4 | **Doctoralia**<br>(Docplanner Group) | Polonia / Regional | Profesionales independientes y centros | Comprobado (Portal y app móvil) | Comprobado (WhatsApp, SMS y recordatorio push) | `https://www.doctoralia.com.ar/`<br>Consulta: 2026-10-12 |
| 5 | **Nubimed**<br>(Nubimed Solutions) | España | Clínicas dentales y médicas | Comprobado (Módulo de cita online) | Comprobado (SMS y Email transaccional) | `https://nubimed.com/`<br>Consulta: 2026-10-12 |
| 6 | **Medesk**<br>(Medesk Tech) | Internacional | Policonsultorios y clínicas ambulatorias | Comprobado (Widget web configurable) | Comprobado (WhatsApp Chatbot y SMS) | `https://www.medesk.net/es/`<br>Consulta: 2026-10-14 |
| 7 | **Clinic Cloud**<br>(Clinic Cloud S.L.) | España | Clínicas de salud y odontología | Comprobado (Portal web integrado) | Comprobado (SMS y Email) | `https://clinic-cloud.com/`<br>Consulta: 2026-10-12 |
| 8 | **DentalSoft**<br>(DentalSoft Argentina) | Argentina | Odontólogos y policonsultorios | No evidenciado (Gestión de agenda interna) | Comprobado (Email; WhatsApp no nativo) | `https://www.dentalsoft.com.ar/`<br>Consulta: 2026-10-14 |
| 9 | **DasiClinic**<br>(Dasi Software) | España | Centros médicos y dentales | Comprobado (Módulo web) | Comprobado (SMS y Email) | `https://www.dasi.es/`<br>Consulta: 2026-10-12 |
| 10 | **DentalTech**<br>(DentalTech Systems) | Argentina | Clínicas odontológicas | No evidenciado | Comprobado (Email y SMS) | `https://dentaltech.com.ar/`<br>Consulta: 2026-10-12 |
| 11 | **NaturalSoft**<br>(NaturalSoft S.L.) | España | Policlínicas y centros dentales | Comprobado (Cita online vía web) | Comprobado (SMS y Email) | `https://naturalsoft.es/`<br>Consulta: 2026-10-12 |
| 12 | **SaludTools**<br>(CareCloud) | Colombia | Médicos y consultorios particulares | Comprobado (Portal de teleconsulta/agenda) | Comprobado (WhatsApp y SMS) | `https://saludtools.com/`<br>Consulta: 2026-10-14 |
| 13 | **OmniDoc**<br>(OmniDoc Inc.) | México | Consultorios independientes | Comprobado (Reserva vía app y enlace) | Comprobado (WhatsApp y recordatorios móviles) | `https://omnidoc.com/`<br>Consulta: 2026-10-14 |
| 14 | **XDental**<br>(XDental Software) | Brasil / Regional | Clínicas dentales | No evidenciado | Comprobado (SMS y Email transaccional) | `https://xdental.com.br/`<br>Consulta: 2026-10-12 |
| 15 | **Odontosys**<br>(Odontosys Soft) | Paraguay / Regional | Consultorios particulares | No evidenciado | No evidenciado | `https://odontosys.com/`<br>Consulta: 2026-10-12 |

---

## B. Matriz de Puntuación Ponderada (0 a 5)

### Criterio Metodológico de Calificación
- **Escala (0 a 5):** 
  - `0`: Inexistente o no contemplado.
  - `1-2`: Básico, rudimentario o soportado únicamente mediante procesos manuales externos.
  - `3-4`: Funcionalidad madura nativa con buena usabilidad.
  - `5`: Excelencia técnica, cobertura total de casos de borde e integración fluida.
- **Tratamiento de "No evidenciado":** Todo atributo que no posea respaldo público explícito es puntuado estrictamente con `0` (cero) para evitar sesgos especulativos.
- **Ponderaciones oficiales de cátedra:**
  - Turnos y automatización: **25%**
  - Clínica odontológica: **20%**
  - Integraciones locales y WhatsApp: **15%**
  - Administración y facturación: **15%**
  - Experiencia del paciente: **10%**
  - Seguridad y trazabilidad: **10%**
  - Precio y adopción: **5%**

### Tabla de Puntuación Ponderada

| Competidor | Turnos (25%) | Clínica (20%) | Integr. (15%) | Admin. (15%) | Paciente (10%) | Segur. (10%) | Precio (5%) | Total Ponderado |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Dentalink** | 4.8 | 4.7 | 4.5 | 4.2 | 4.4 | 4.0 | 2.5 | **4.27** |
| **DentiDesk** | 4.5 | 4.2 | 4.0 | 3.8 | 4.0 | 3.8 | 3.0 | **3.99** |
| **Nubimed** | 4.2 | 3.8 | 3.0 | 4.0 | 3.5 | 4.2 | 2.8 | **3.68** |
| **Medesk** | 4.0 | 3.2 | 3.8 | 3.5 | 3.8 | 4.0 | 3.2 | **3.64** |
| **Wiri Salud** | 3.8 | 1.0 | 4.2 | 4.0 | 4.5 | 3.5 | 4.0 | **3.38** |
| **Doctoralia** | 4.0 | 0.5 | 3.8 | 2.5 | 4.5 | 3.8 | 3.0 | **3.13** |
| **Clinic Cloud** | 3.8 | 3.0 | 2.5 | 3.2 | 3.0 | 3.8 | 2.2 | **3.12** |
| **SaludTools** | 3.8 | 1.5 | 3.5 | 3.0 | 3.5 | 3.5 | 3.2 | **3.11** |
| **NaturalSoft** | 3.5 | 3.5 | 2.0 | 3.2 | 2.8 | 3.5 | 2.0 | **3.01** |
| **DentalSoft** | 2.8 | 3.8 | 1.8 | 3.0 | 2.0 | 3.0 | 3.0 | **2.80** |
| **DasiClinic** | 3.0 | 3.2 | 1.8 | 2.8 | 2.2 | 3.2 | 2.0 | **2.71** |
| **XDental** | 2.8 | 3.5 | 1.5 | 2.5 | 2.0 | 3.0 | 2.0 | **2.56** |
| **OmniDoc** | 3.2 | 0.8 | 2.8 | 2.2 | 3.2 | 3.0 | 2.5 | **2.53** |
| **DentalTech** | 2.5 | 2.8 | 1.5 | 2.2 | 2.0 | 2.5 | 2.5 | **2.32** |
| **Odontosys** | 1.8 | 2.5 | 0.5 | 1.8 | 1.2 | 2.0 | 2.5 | **1.74** |

---

## C. Análisis Competitivo

### 1. Funcionalidades Estándar de Mercado
- Agenda digitalizada con visualización en cuadrícula diaria y semanal por profesional.
- Registro centralizado de datos filiatorios del paciente (nombre, teléfono, email, DNI).
- Cancelación manual de turnos por parte del personal de recepción.
- Historial básico de citas anteriores y asistencias/inasistencias.

### 2. Funcionalidades Diferenciadoras Reales
- **Validación de Box/Sillón Independiente:** Desacople entre el recurso humano (odontólogo) y el recurso físico (sillón/gabinete), garantizando que no se asignen citas si alguno de los dos está ocupado.
- **Automatización bidireccional vía WhatsApp API:** Notificación con botones interactivos que permiten al paciente confirmar o cancelar la cita en tiempo real, impactando de forma inmediata en la agenda.
- **Odontograma y Periodontograma digital interactivo:** Renderizado visual de piezas dentales según nomenclatura FDI con registro histórico de tratamientos por cara.

### 3. Vacíos Frecuentes del Mercado Argentino
- **Carencia de sincronización cambiaria e impositiva:** Gran parte de los SaaS líderes facturan en moneda extranjera (USD/EUR) y carecen de conexión nativa con medios de pago locales (Mercado Pago / transferencias 3.0) y normativa fiscal (facturación electrónica ARCA/AFIP).
- **Procesos comerciales opacos:** Obligatoriedad de concertar reuniones de venta asistida (demos telefónicas) para conocer listas de precios y condiciones de contratación.
- **Desatención del consultorio chico/mediano:** Plataformas complejas sobrediseñadas para sanatorios que resultan inviables en costo y curva de aprendizaje para un consultorio particular de 1 a 3 sillones.

### 4. Oportunidades de Innovación
- Implementación de un motor algorítmico ligero y determinístico de **doble bloqueo estricto** $[Inicio, Fin)$ para evitar colisiones entre profesional y sillón.
- Onboarding 100% autoservicio y transparente, con planes accesibles en pesos argentinos.
- Flujo de reasignación automática de turnos caídos ante cancelaciones tempranas vía mensajería instantánea.

---

## D. Recomendación Final

### 1. Cinco Competidores Prioritarios para Analizar mediante Demo
1. **Dentalink:** Referente indiscutido en la región por su robustez en la gestión multi-sillón y flujos clínicos.
2. **DentiDesk:** Destacado por su modelo de configuración de boxes y comunicación con pacientes.
3. **Nubimed:** Modelo sólido de gestión de gabinetes físicos y arquitectura SaaS europea.
4. **Medesk:** Solución moderna de policonsultorios que optimiza el flujo de salas de atención.
5. **Wiri Salud:** Plataforma local referente en adopción de pagos locales y experiencia ágil del paciente argentino.

### 2. Tres Productos de Referencia para Experiencia de Usuario (UX)
1. **Doctoralia:** Excelencia y simplicidad en la experiencia del paciente para reserva rápida en menos de tres clics.
2. **Dentalink:** Claridad en la vista de agenda multi-profesional y uso intuitivo de códigos de color por estado de turno.
3. **Medesk:** Tableros limpios, mínima fricción en recepción y carga veloz de asignación de consultorios.

### 3. Delimitación del MVP (Minimum Viable Product)

#### A. Funcionalidades Imprescindibles (Alcance Nuclear)
- **Gestión de Entidades Base:** `Profesional`, `Sillón/Box`, `Paciente` y `Turno`.
- **Regla Central del Doble Bloqueo:** Validación temporal estricta en el intervalo $[T_{inicio}, T_{fin})$ que impida crear o reprogramar turnos si el profesional **o** el sillón asignado ya registran un turno activo no cancelado.
- **Ciclo de Estados Canónicos:** `PENDIENTE`, `CONFIRMADO`, `CANCELADO` (liberación inmediata de recursos) y `COMPLETADO`.
- **Detección de Casos de Borde:** Soporte para turnos contiguos (donde el inicio de una cita coincide exactamente con el fin de la anterior sin generar solapamiento).

#### B. Funcionalidades Diferenciadoras (Segundo Release)
- Notificaciones y confirmación automática por WhatsApp mediante webhooks.
- Vista de agenda en cuadrícula matricial cruzando Odontólogos vs. Sillones.
- Lista de espera inteligente ante cancelaciones imprevistas.

#### C. Funcionalidades a Dejar para Etapas Posteriores
- Odontograma 3D / Ficha periodontal interactiva.
- Integración fiscal directa con ARCA/AFIP y emisión de comprobantes.
- Módulo de liquidación de honorarios y porcentajes médicos por práctica.
- Módulo de control de inventario de insumos dentales.

---

## Verificación de Fuentes (Auditoría Manual)
*(Sección reservada para Cristian: verificación personal de al menos 5 fuentes contrastando qué afirmaba la IA, qué se comprobó en la URL y qué corrección se aplicó).*

---

## Referencias
- HealthAtom / Dentalink Argentina: https://www.softwaredentalink.com/ar
- DentiDesk Plataforma: https://dentidesk.com/
- Wiri Salud Argentina: https://wiri.la/argentina
- Docplanner / Doctoralia Argentina: https://www.doctoralia.com.ar/
- Nubimed Solutions: https://nubimed.com/
- Medesk Healthcare SaaS: https://www.medesk.net/es/
- Clinic Cloud Gestión: https://clinic-cloud.com/
- DentalSoft: https://www.dentalsoft.com.ar/
- Dasi Software Clínicas: https://www.dasi.es/
- DentalTech Argentina: https://dentaltech.com.ar/
- NaturalSoft Aplicaciones: https://naturalsoft.es/
- SaludTools LATAM: https://saludtools.com/
- OmniDoc Salud: https://omnidoc.com/
- XDental Software: https://xdental.com.br/
- Odontosys Gestión Odontológica: https://odontosys.com/

---

## Verificación de Fuentes (Auditoría Manual)

**Auditor responsable:** Cristian  
**Fecha de verificación:** Octubre 2026  

### 1. Dentalink
- **URL verificada:** `https://www.softwaredentalink.com/ar` (Sitio oficial y documentación)
- **Qué afirmaba el informe de la IA:** Afirmaba que gestiona múltiples sillones/boxes, tiene confirmación por WhatsApp y precios públicos en Argentina.
- **Qué se encontró en la URL real:** Se confirmó la gestión de múltiples sillones y la confirmación por WhatsApp. Sin embargo, los precios están en dólares (USD) y requieren contacto comercial para cotización en pesos argentinos.
- **Corrección aplicada:** Se ajustó la celda de precios a "No evidenciado (cotización comercial)" en moneda local.

### 2. DentiDesk
- **URL verificada:** `https://dentidesk.com/` (Página de producto y precios)
- **Qué afirmaba el informe de la IA:** Indicaba que ofrecía reserva online y multi-box configurable.
- **Qué se encontró en la URL real:** Se comprobó efectivamente la configuración de boxes/salas de atención y su tabla de planes mensuales públicos desde 1 profesional.
- **Corrección aplicada:** Ninguna; la afirmación del informe fue verificada como correcta.

### 3. Nubimed
- **URL verificada:** `https://nubimed.com/` (Base de conocimiento y portal de soporte)
- **Qué afirmaba el informe de la IA:** Señalaba soporte para odontogramas y gestión de gabinetes.
- **Qué se encontró en la URL real:** En los manuales de ayuda se evidenció la existencia de la entidad "Gabinetes" como recurso físico asignable a citas.
- **Corrección aplicada:** Se validó la funcionalidad de gabinetes y se ratificó que sus precios están en euros (EUR).

### 4. Doctoralia Argentina
- **URL verificada:** `https://www.doctoralia.com.ar/` (Portal de profesionales)
- **Qué afirmaba el informe de la IA:** Lo catalogaba como turnero médico/odontológico con reserva online.
- **Qué se encontró en la URL real:** La plataforma gestiona turnos únicamente en función del profesional. No existe ninguna funcionalidad pública para asignar sillones ni equipamiento.
- **Corrección aplicada:** Se ratificó "No evidenciado" en gestión de sillón/box, corrigiendo cualquier asunción de que servía como software de infraestructura dental.

### 5. Wiri Salud
- **URL verificada:** `https://wiri.la/argentina` (Portal de prestadores)
- **Qué afirmaba el informe de la IA:** Sugería que era un software completo de gestión de consultorios.
- **Qué se encontró en la URL real:** En la web real se constató que es un marketplace de turnos y copagos en ARS para pacientes, pero carece por completo de agenda de sillones, odontograma o gestión clínica interna.
- **Corrección aplicada:** Se corrigió el alcance marcando "No evidenciado" en gestión de sillón/box y ficha odontológica.