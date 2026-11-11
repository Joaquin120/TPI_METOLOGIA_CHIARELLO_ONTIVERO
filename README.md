# Sistema de Gestión de Turnos Odontológicos (SaaS Multi-tenant)

Sistema web integral para la gestión y optimización de agendas odontológicas clínicas. Resuelve la **doble restricción física simultánea** (disponibilidad de profesional y sillón/box de atención en intervalos semiabiertos $[T_{inicio}, T_{fin})$), con soporte multi-tenant nativo, auditoría inmutable, notificaciones reactivas y lista de espera FIFO.

El proyecto fue concebido, especificado y construido bajo la metodología **Spec-Driven Development (SDD)** con **OpenSpec** y arquitectura hexagonal estricta (puertos y adaptadores), alcanzando la **Versión 1.0.0** con 16 especificaciones canónicas consolidadas y 413 tests automatizados pasando al 100%.

---

## Características Principales

- **Arquitectura Hexagonal Pura:** Dominio aislado (`backend/src/domain/`) con cero dependencias de frameworks, ORMs o librerías externas (verificado por guard tests automáticos).
- **Aislamiento Multi-Tenant & RBAC:** Resolución determinista de inquilino y control de acceso basado en roles (`Administrador`, `Recepcionista`, `Profesional`) mediante tokens JWT (HS256) y almacenamiento criptográfico seguro de contraseñas.
- **Gestión Clínica Completa:** Administración de profesionales, sillones, pacientes, estados asistenciales de turnos y reprogramación in-place.
- **Mantenimiento Preventivo:** Bloqueo de sillones por mantenimiento con salvaguardas operativas bidireccionales.
- **Analítica y Trazabilidad:** Indicadores operativos de ocupación y bitácora inmutable de eventos clínicos/administrativos.
- **Frontend SPA Responsivo:** Interfaz moderna en React 18 + Vite + TypeScript con navegación protegida, agenda interactiva y grilla matricial de turnos.
- **Integraciones Reactivas (Fase 5):** Notificaciones y confirmación/cancelación de turnos vía webhooks interactivos de WhatsApp, y gestión reactiva de lista de espera con asignación automática ante vacantes.

---

## Requisitos Previos

- **Python 3.11** o superior.
- **Node.js v18** o superior y **npm**.
- **Git**.

---

## Instalación y Puesta en Marcha

### 1. Clonar el repositorio
```bash
git clone https://github.com/Joaquin120/TPI_CHIARELLO_OLIVEROS_ONTIVERO_RODRIGUEZ_METODOLOGIA1.git
cd TPI_METOLOGIA_CHIARELLO_ONTIVERO
```

### 2. Backend (FastAPI + SQLite)

```bash
# Navegar a la carpeta de backend
cd backend

# Crear y activar el entorno virtual
# En Windows (PowerShell):
python -m venv venv
.\venv\Scripts\Activate.ps1

# En Linux/macOS:
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Inicializar base de datos y sembrar datos sintéticos de prueba
python -c "from src.api.app import create_app; create_app(sembrar=True)"

# Iniciar servidor de desarrollo (puerto 8000)
python -m uvicorn src.api.app:create_app --factory --reload
```

### 3. Frontend (React + Vite + TypeScript)

En una nueva terminal:

```bash
# Navegar a la carpeta de frontend
cd frontend

# Instalar dependencias
npm install

# Iniciar servidor de desarrollo web (puerto 5173)
npm run dev
```

La aplicación web estará disponible en `http://localhost:5173`.

---

## Ejecución de Pruebas Automatizadas (Strict TDD)

El proyecto cuenta con un 100% de éxito en su suite de pruebas (413 tests en verde sin regresiones):

### Pruebas de Backend (Pytest)
Desde la carpeta `backend/` con el entorno virtual activado:
```bash
pytest -v
```
> **Cobertura:** 348 tests verificando pureza de dominio, persistencia SQLite real, aislamiento multi-tenant, seguridad RBAC y contratos de la API REST.

### Pruebas de Frontend (Vitest)
Desde la carpeta `frontend/`:
```bash
npm test
```
> **Cobertura:** 65 tests comprobando renderizado de componentes, navegación, manejo de contexto de autenticación y vistas de agenda.

---

## Resumen de la API REST (`/api/v1`)

Todos los endpoints requieren autenticación mediante cabecera `Authorization: Bearer <token>` (excepto `/health` y `/auth/login`).

| Módulo | Endpoint Principal | Descripción |
|---|---|---|
| **Salud** | `GET /api/v1/health` | Verificación de disponibilidad del servicio. |
| **Auth** | `POST /api/v1/auth/login`<br>`GET /api/v1/auth/me` | Inicio de sesión, emisión de JWT y perfil autenticado. |
| **Turnos** | `POST /api/v1/turnos`<br>`GET /api/v1/turnos`<br>`PATCH /api/v1/turnos/{id}/estado`<br>`PATCH /api/v1/turnos/{id}/reprogramar` | Operación completa de agenda con validación de doble candado físico. |
| **Recursos** | `GET/POST /api/v1/profesionales`<br>`GET/POST /api/v1/sillones` | Catálogo y administración de profesionales y sillones odontológicos. |
| **Pacientes** | `POST /api/v1/pacientes`<br>`GET /api/v1/pacientes` | Registro y consulta de pacientes acotados por tenant. |
| **Bloqueos** | `GET/POST/DELETE /api/v1/bloqueos` | Inhabilitación temporal de sillones por mantenimiento asistencial. |
| **Métricas** | `GET /api/v1/metricas/turnos`<br>`GET /api/v1/metricas/recursos` | Métricas operativas, tasas de ocupación y cancelación. |
| **Auditoría** | `GET /api/v1/auditoria` | Bitácora inmutable de eventos clínicos y de seguridad. |
| **WhatsApp** | `POST /api/v1/webhooks/whatsapp` | Webhook interactivo para confirmación y cancelación de citas. |
| **Lista de Espera** | `POST /api/v1/lista-espera`<br>`GET /api/v1/lista-espera`<br>`POST /api/v1/lista-espera/{id}/asignar` | Cola FIFO reactiva para asignación automática de vacantes. |

### Contrato de Error Unificado

Todas las excepciones de negocio y validación devuelven una estructura uniforme:

```json
{
  "error": {
    "code": "SOLAPAMIENTO_PROFESIONAL",
    "message": "El profesional ya posee un turno asignado en el intervalo solicitado."
  }
}
```

---

## Estructura del Repositorio

```text
├── openspec/                     # Especificaciones canónicas (16) y archivo histórico de changes
│   ├── specs/                    # Especificaciones maestras validadas
│   └── changes/archive/          # Historial de changes C-01 a C-15 archivados
├── backend/                      # Servicio Backend FastAPI
│   ├── src/
│   │   ├── domain/               # Núcleo de dominio puro (modelos, puertos, servicios)
│   │   ├── repositories/         # Adaptadores de persistencia SQLite
│   │   ├── infrastructure/       # Migraciones SQL, seed de datos y base de datos
│   │   └── api/                  # Routers, esquemas Pydantic y middlewares de seguridad
│   └── tests/                    # Suite de 348 pruebas con pytest
├── frontend/                     # Cliente Web SPA
│   ├── src/                      # Componentes React, hooks, contexts y páginas
│   └── tests/                    # Suite de 65 pruebas con Vitest
├── knowledge-base/               # Documentación canónica de arquitectura, reglas y flujos
└── CHANGES.md                    # Registro y trazabilidad de los 15 changes del Roadmap
```

---

## Integración MCP: Filesystem Server

### Configuración del cliente (JSON)

Para permitir a los agentes de IA inspeccionar de forma determinista la base de conocimiento y el archivo de especificaciones:

```json
{
  "mcp": {
    "filesystem": {
      "type": "local",
      "command": [
        "npx",
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "."
      ],
      "environment": {},
      "enabled": true
    }
  }
}
```

---

## Integrantes del Equipo

- Joaquín Chiarello
- Santiago Ontivero