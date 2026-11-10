# Tasks

## 1. Configuración y Scaffolding Base del Frontend

- [x] 1.1 Crear estructura de directorios en `frontend/`, `package.json`, `tsconfig.json`, `tsconfig.node.json`, `index.html` y `.env.example`; verificar instalación limpia de dependencias con `npm install`.
- [x] 1.2 Configurar `vite.config.ts` con soporte React, proxy hacia backend FastAPI (`/api/v1` -> `http://localhost:8000`) y runner Vitest con jsdom; verificar ejecución del runner con `npm test -- --run`.

## 2. Tipos de Dominio y Cliente HTTP Tipado

- [x] 2.1 Definir interfaces y tipos TypeScript en `frontend/src/types/index.ts` espejando los modelos y esquemas del backend (`Usuario`, `Rol`, `Turno`, `Paciente`, `Profesional`, `Sillon`, `Bloqueo`, `ErrorEnvelope`); verificar compilación de tipos con `npx tsc --noEmit`.
- [x] 2.2 Implementar cliente HTTP centralizado en `frontend/src/api/cliente.ts` con soporte de baseURL, inyección automática de `Authorization: Bearer <token>`, parseo del envelope de error y callback ante HTTP 401; verificar con pruebas unitarias en `frontend/tests/cliente.test.ts`.
- [x] 2.3 Implementar módulos de API tipados en `frontend/src/api/` (`auth.ts`, `turnos.ts`, `recursos.ts`, `pacientes.ts`); verificar tipado estricto con `npx tsc --noEmit`.

## 3. Autenticación, Gestión de Sesión y Guardián RBAC

- [x] 3.1 Implementar `AuthContext` y hook `useAuth` en `frontend/src/context/AuthContext.tsx` con manejo de sesión, almacenamiento local y cierre de sesión; verificar con pruebas unitarias en `frontend/tests/auth-context.test.tsx`.
- [x] 3.2 Implementar componente `ProtectedRoute` en `frontend/src/components/ProtectedRoute.tsx` evaluando autenticación y roles autorizados (`rolesPermitidos`); verificar escenarios de redirección a login y acceso denegado en `frontend/tests/protected-route.test.tsx`.

## 4. Layout General, Navegación Contextual y Vistas Base

- [x] 4.1 Implementar estilos clínicos base en `frontend/src/index.css` y componentes de estructura (`Navbar.tsx`, `Sidebar.tsx`, `Layout.tsx`) con navegación contextual por rol (`Administrador`, `Recepcionista`, `Profesional`) y botón de cerrar sesión; verificar renderizado contextual en `frontend/tests/layout.test.tsx`.
- [x] 4.2 Implementar vista de autenticación `Login.tsx` con captura de credenciales y feedback de error, y vistas base `Agenda.tsx`, `Pacientes.tsx`, `Recursos.tsx` y `Auditoria.tsx`; verificar renderizado e integración en `frontend/src/App.tsx` con pruebas en `frontend/tests/app-routing.test.tsx`.

## 5. Verificación Integral y No Regresión

- [x] 5.1 Ejecutar suite completa de frontend (`npm test -- --run` y `npm run build`); verificar 100% de tests pasando y generación correcta del bundle.
- [x] 5.2 Ejecutar suite completa del backend (`pytest backend/tests --cov=src`); verificar que los 303 tests existentes sigan pasando al 100% verde sin regresiones.
