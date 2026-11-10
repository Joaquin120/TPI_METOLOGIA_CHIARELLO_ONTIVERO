# Proposal

## Why

El producto está concebido como una plataforma SaaS web-first (`architecture.md` §1, `actors.md` §4, `D-01`), orientada a recepcionistas, administradores y odontólogos de consultorios y clínicas. Hasta el momento, todas las funcionalidades se implementaron y probaron en el backend a través de endpoints REST/JSON desacoplados del dominio (`C-01` a `C-10`).

Este cambio introduce la capacidad `cliente-web-shell` (Change `c-11-frontend-shell`), estableciendo el scaffolding del cliente web SPA (React, TypeScript y Vite), autenticación contra el backend mediante JWT (`POST /api/v1/auth/login`), gestión de sesión de usuario y rutas protegidas con control de acceso basado en roles (RBAC), layout responsivo con navegación estructurada (Agenda, Pacientes, Recursos, Auditoría y Configuración) y cliente HTTP tipado, sentando las bases visuales y arquitectónicas para la interacción operativa de la agenda (`C-12`).

## What Changes

- **Estructura y Scaffolding del Frontend (`frontend/`)**:
  - Inicialización del proyecto web cliente con Vite, React 18+ y TypeScript (`tsconfig.json`, `package.json`, `vite.config.ts`, `index.html`).
  - Configuración de proxy de desarrollo hacia el backend FastAPI (`/api/v1` -> `http://localhost:8000`).
  - Configuración de variables de entorno con `frontend/.env.example` (`VITE_API_BASE_URL`).
  - Soporte de estilos modernos, limpios y accesibles siguiendo las pautas de diseño clínico (`emil-design-eng`, diseño sobrio sin artificios).
- **Cliente HTTP y Tipado API (`frontend/src/api/`)**:
  - Cliente HTTP centralizado (`api/cliente.ts`) que gestiona tokens JWT (almacenamiento en `localStorage`/memoria), inyección automática del header `Authorization: Bearer <token>` y captura uniforme de errores según el envelope `{"error": {"code": "...", "message": "..."}}`.
  - Módulos de API tipados contra los contratos del backend: autenticación (`auth.ts`), turnos (`turnos.ts`), recursos (`recursos.ts`), pacientes (`pacientes.ts`) y auditoría (`auditoria.ts`).
- **Autenticación y Contexto de Usuario (`frontend/src/context/AuthContext.tsx`)**:
  - Estado global de autenticación: `usuario` (id, email, tenant_id, rol, nombre), `token`, `estaAutenticado`, `iniciarSesion(credenciales)` y `cerrarSesion()`.
  - Persistencia segura del token de sesión y expiración controlada con redirección automática ante token inválido o vencido (HTTP 401).
- **Navegación y Rutas Protegidas (`frontend/src/components/`, `frontend/src/pages/`)**:
  - Componente `RutaProtegida` (`ProtectedRoute.tsx`): redirige a `/login` si el usuario no está autenticado; restringe el acceso y muestra pantalla de acceso no autorizado si el rol del usuario no coincide con los permisos requeridos.
  - Layout general (`Layout.tsx`): barra de navegación superior (usuario, clínica/tenant, botón de cierre de sesión) y barra lateral (Sidebar) con enlaces contextuales según el rol:
    - `Recepcionista`: Agenda, Pacientes, Recursos.
    - `Administrador`: Agenda, Pacientes, Recursos, Auditoría, Métricas.
    - `Profesional`: Agenda propia.
  - Vistas base:
    - `/login`: Formulario de inicio de sesión con email, contraseña, validación y feedback visual de credenciales incorrectas.
    - `/agenda`: Shell contenedor de la agenda (listo para `C-12`).
    - `/pacientes`: Vista de pacientes registrados.
    - `/recursos`: Vista de profesionales y sillones/boxes.
    - `/auditoria`: Vista de bitácora inmutable (restringida a Administrador).
- **Pruebas Automatizadas del Frontend (`frontend/tests/`)**:
  - Configuración de runner de pruebas con Vitest / Testing Library.
  - Pruebas de render de login, validación de credenciales inválidas, redirección de rutas no autenticadas hacia `/login` y denegación de rutas protegidas por rol.

## Capabilities

### New Capabilities
- `cliente-web-shell`: Scaffolding y estructura base de la aplicación web cliente SPA, gestión de autenticación JWT y sesión de usuario, protección de rutas por rol RBAC, layout responsivo con navegación y cliente HTTP tipado contra la API REST.

### Modified Capabilities
*(Ninguna. El backend conserva sus contratos y especificaciones vigentes).*

## Impact

- **Código y Directorios**:
  - Nuevo directorio `frontend/` en la raíz del repositorio con su configuración de build y dependencias independientes.
  - Ningún archivo existente en `backend/` se modifica; se consume la API REST/JSON actual.
- **Configuración y DevOps**:
  - Documentación de variables de entorno para frontend en `frontend/.env.example`.
  - Comandos de desarrollo: `npm run dev` para el servidor de desarrollo Vite y `npm test` para la ejecución de pruebas.
