# Tasks

## 1. Dominio y Persistencia de Lista de Espera

- [x] 1.1 Definir la entidad `EntradaListaEspera`, constantes de estado (`EstadoListaEspera`: `PENDIENTE`, `NOTIFICADO`, `ASIGNADO`, `CANCELADO`) y el puerto abstracto `PuertoListaEspera` en `backend/src/domain/`. Verificar mediante tests unitarios de contrato en `backend/tests/test_lista_espera_dominio.py`.
- [x] 1.2 Crear la migración `008_lista_espera.sql` e implementar `RepositorioListaEsperaSqlite` con aislamiento por `tenant_id` y ordenamiento de prioridad FIFO (`creado_en ASC`). Verificar con tests de persistencia sobre SQLite real en `backend/tests/test_lista_espera_repositorio.py`.

## 2. Servicio de Dominio y Detección de Candidatos

- [x] 2.1 Implementar `ServicioListaEspera` con métodos para registrar solicitudes, filtrar por fecha/profesional/estado, cancelar entradas y recuperar candidatos prioritarios para un intervalo (`PA-14`). Verificar mediante tests unitarios en `backend/tests/test_lista_espera_servicio.py`.
- [x] 2.2 Integrar la cancelación de turnos en `ServicioTurnos` para que busque candidatos en lista de espera y despache una notificación de vacante mediante `NotificacionesService` sin bloquear la cancelación. Verificar con tests de integración en `backend/tests/test_turnos_cancelacion_lista_espera.py`.

## 3. Endpoints REST y Reasignación a Turnos

- [x] 3.1 Implementar los endpoints `POST /api/v1/lista-espera`, `GET /api/v1/lista-espera` y `PATCH /api/v1/lista-espera/{id}/cancelar` protegidos con RBAC (`Recepcionista`, `Administrador`) y esquemas Pydantic. Verificar mediante tests en `backend/tests/test_api_lista_espera.py`.
- [x] 3.2 Implementar el endpoint `POST /api/v1/lista-espera/{id}/asignar` para convertir la entrada en un turno confirmado validando disponibilidad física del sillón y profesional (`RN-01`, `RN-08`) y registrando auditoría (`C-09`). Verificar mediante tests en `backend/tests/test_api_lista_espera.py`.

## 4. Verificación Integral del Sistema

- [x] 4.1 Ejecutar la suite completa de tests de backend con `pytest` y de frontend con `npm test -- --run` para verificar cero regresiones y 100% de pruebas en verde.

