"""Servicio de dominio para el agendamiento de turnos odontológicos."""

from dataclasses import replace
import logging

from src.domain.exceptions import (
    BloqueoNoEncontradoError,
    BloqueoSolapadoError,
    ConflictoTurnosExistentesError,
    SillonBloqueadoError,
    SolapamientoProfesionalError,
    SolapamientoSillonError,
    TransicionInvalidaError,
)
from src.domain.models import (
    CANCELADO,
    COMPLETADO,
    CONFIRMADO,
    ESTADOS_ACTIVOS,
    PENDIENTE,
    BloqueoSillon,
    Profesional,
    Sillon,
    Turno,
)
from src.domain.lista_espera import ServicioListaEspera
from src.domain.notificaciones import NotificacionesService
from src.domain.puertos import PuertoBloqueos, PuertoTurnos

logger = logging.getLogger(__name__)

# Lista blanca de transiciones válidas: (estado_actual, acción) → estado_destino.
_TRANSICIONES: dict[tuple[str, str], str] = {
    (PENDIENTE, "confirmar"): CONFIRMADO,
    (PENDIENTE, "cancelar"): CANCELADO,
    (CONFIRMADO, "cancelar"): CANCELADO,
    (CONFIRMADO, "completar"): COMPLETADO,
}


class ServicioTurnos:
    """Registra turnos y bloqueos validando disponibilidad y solapamientos."""

    def __init__(
        self,
        repositorio: PuertoTurnos,
        puerto_bloqueos: PuertoBloqueos | None = None,
        servicio_notificaciones: NotificacionesService | None = None,
        servicio_lista_espera: ServicioListaEspera | None = None,
    ) -> None:
        self._repositorio: PuertoTurnos = repositorio
        self._puerto_bloqueos: PuertoBloqueos | None = puerto_bloqueos
        self._servicio_notificaciones: NotificacionesService | None = servicio_notificaciones
        self._servicio_lista_espera: ServicioListaEspera | None = servicio_lista_espera

    def agendar_turno(
        self,
        paciente: str,
        fecha: str,
        hora_inicio: str,
        hora_fin: str,
        profesional: Profesional,
        sillon: Sillon,
        telefono_paciente: str | None = None,
    ) -> Turno:
        """Crea y registra un turno si no hay solapamiento ni bloqueos de sillón."""
        sillon_id = sillon.id
        if sillon_id is None and hasattr(self._repositorio, "_repo_sillones"):
            sillon_id = self._repositorio._repo_sillones.resolver_id(sillon.nombre)
            sillon = replace(sillon, id=sillon_id)

        inicio_str = f"{fecha} {hora_inicio}"
        fin_str = f"{fecha} {hora_fin}"

        # Validación de sillón bloqueado por mantenimiento (C-10, F-12, RN-07)
        if self._puerto_bloqueos is not None and sillon_id is not None:
            bloqueos = self._puerto_bloqueos.buscar_bloqueos_solapados(
                sillon_id=sillon_id,
                fecha_hora_inicio=inicio_str,
                fecha_hora_fin=fin_str,
            )
            if bloqueos:
                raise SillonBloqueadoError(
                    f"El sillón {sillon.nombre} se encuentra bloqueado por mantenimiento "
                    f"el {fecha} de {hora_inicio} a {hora_fin}"
                )

        candidatos = self._repositorio.buscar_activos_solapables(
            fecha=fecha,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            profesional=profesional,
            sillon=sillon,
        )

        for turno_existente in candidatos:
            # Doble validación de recurso: profesional y sillón, de forma independiente.
            # Precedencia RN-09: se valida profesional primero, sillón segundo.
            if (
                turno_existente.profesional == profesional
                or turno_existente.profesional.nombre == profesional.nombre
            ):
                raise SolapamientoProfesionalError(
                    f"El profesional {profesional.nombre} ya tiene un turno "
                    f"el {fecha} de {turno_existente.hora_inicio} a {turno_existente.hora_fin}"
                )
            if (
                turno_existente.sillon == sillon
                or turno_existente.sillon.nombre == sillon.nombre
            ):
                raise SolapamientoSillonError(
                    f"El sillón {sillon.nombre} ya está ocupado "
                    f"el {fecha} de {turno_existente.hora_inicio} a {turno_existente.hora_fin}"
                )

        turno = Turno(
            profesional=profesional,
            sillon=sillon,
            fecha=fecha,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            paciente=paciente,
        )
        guardado = self._repositorio.guardar(turno)

        if self._servicio_notificaciones is not None:
            try:
                self._servicio_notificaciones.notificar_alta(
                    paciente=paciente,
                    telefono=telefono_paciente,
                    profesional=profesional.nombre,
                    fecha=fecha,
                    hora_inicio=hora_inicio,
                    turno_id=guardado.id,
                )
            except Exception as err:
                logger.error("Error no bloqueante al notificar alta por WhatsApp: %s", err, exc_info=True)

        return guardado

    def reprogramar(
        self,
        turno_id: int,
        nueva_fecha: str,
        nueva_hora_inicio: str,
        nueva_hora_fin: str,
        nuevo_profesional: Profesional | None = None,
        nuevo_sillon: Sillon | None = None,
    ) -> Turno:
        """Reprograma un turno existente preservando su identidad y estado activo (F-09, RP-03).

        Valida que el turno exista y se encuentre en estado activo (PENDIENTE o CONFIRMADO).
        Rechaza turnos cancelados o completados con TransicionInvalidaError.
        Aplica el doble candado simultáneo e independiente de disponibilidad con precedencia RN-09.
        Excluye el turno actual de la validación para soportar desplazamientos parciales.
        """
        turno = self._repositorio.obtener_por_id(turno_id)
        if turno is None:
            raise ValueError(f"El turno {turno_id} no existe")

        if turno.estado not in ESTADOS_ACTIVOS:
            raise TransicionInvalidaError(
                f"No se puede reprogramar un turno en estado '{turno.estado}'"
            )

        prof_efectivo = (
            nuevo_profesional if nuevo_profesional is not None else turno.profesional
        )
        sillon_efectivo = nuevo_sillon if nuevo_sillon is not None else turno.sillon

        sillon_id = sillon_efectivo.id
        if sillon_id is None and hasattr(self._repositorio, "_repo_sillones"):
            sillon_id = self._repositorio._repo_sillones.resolver_id(sillon_efectivo.nombre)
            sillon_efectivo = replace(sillon_efectivo, id=sillon_id)

        nueva_inicio_str = f"{nueva_fecha} {nueva_hora_inicio}"
        nueva_fin_str = f"{nueva_fecha} {nueva_hora_fin}"

        # Comprobación de sillón bloqueado en reprogramación (C-10)
        if self._puerto_bloqueos is not None and sillon_id is not None:
            bloqueos = self._puerto_bloqueos.buscar_bloqueos_solapados(
                sillon_id=sillon_id,
                fecha_hora_inicio=nueva_inicio_str,
                fecha_hora_fin=nueva_fin_str,
            )
            if bloqueos:
                raise SillonBloqueadoError(
                    f"El sillón {sillon_efectivo.nombre} se encuentra bloqueado por mantenimiento "
                    f"el {nueva_fecha} de {nueva_hora_inicio} a {nueva_hora_fin}"
                )

        candidatos = self._repositorio.buscar_activos_solapables(
            fecha=nueva_fecha,
            hora_inicio=nueva_hora_inicio,
            hora_fin=nueva_hora_fin,
            profesional=prof_efectivo,
            sillon=sillon_efectivo,
            excluir_turno_id=turno.id,
        )

        for turno_existente in candidatos:
            if (
                turno_existente.profesional == prof_efectivo
                or turno_existente.profesional.nombre == prof_efectivo.nombre
            ):
                raise SolapamientoProfesionalError(
                    f"El profesional {prof_efectivo.nombre} ya tiene un turno "
                    f"el {nueva_fecha} de {turno_existente.hora_inicio} a {turno_existente.hora_fin}"
                )
            if (
                turno_existente.sillon == sillon_efectivo
                or turno_existente.sillon.nombre == sillon_efectivo.nombre
            ):
                raise SolapamientoSillonError(
                    f"El sillón {sillon_efectivo.nombre} ya está ocupado "
                    f"el {nueva_fecha} de {turno_existente.hora_inicio} a {turno_existente.hora_fin}"
                )

        turno_actualizado = replace(
            turno,
            fecha=nueva_fecha,
            hora_inicio=nueva_hora_inicio,
            hora_fin=nueva_hora_fin,
            profesional=prof_efectivo,
            sillon=sillon_efectivo,
        )
        return self._repositorio.actualizar_reprogramacion(turno_actualizado)

    def crear_bloqueo(
        self,
        tenant_id: int,
        sillon_id: int,
        fecha: str | None = None,
        hora_inicio: str | None = None,
        hora_fin: str | None = None,
        motivo: str = "",
        creado_por: int | None = None,
        fecha_hora_inicio: str | None = None,
        fecha_hora_fin: str | None = None,
        inicio: object = None,
        fin: object = None,
    ) -> BloqueoSillon:
        """Crea un bloqueo temporal de sillón aplicando salvaguardas (RP-07, RN-07)."""
        if fecha_hora_inicio and fecha_hora_fin:
            f_inicio, f_fin = fecha_hora_inicio, fecha_hora_fin
        elif fecha and hora_inicio and hora_fin:
            f_inicio, f_fin = f"{fecha} {hora_inicio}", f"{fecha} {hora_fin}"
        elif inicio and fin:
            f_inicio = inicio.strftime("%Y-%m-%d %H:%M") if hasattr(inicio, "strftime") else str(inicio)
            f_fin = fin.strftime("%Y-%m-%d %H:%M") if hasattr(fin, "strftime") else str(fin)
        else:
            raise ValueError("Parámetros de intervalo incompletos")

        if f_inicio >= f_fin:
            raise ValueError("hora_inicio debe ser anterior a hora_fin")

        # 1. Verificar bloqueos solapados previos en el sillón
        if self._puerto_bloqueos is not None:
            solapados = self._puerto_bloqueos.buscar_bloqueos_solapados(
                sillon_id=sillon_id,
                fecha_hora_inicio=f_inicio,
                fecha_hora_fin=f_fin,
            )
            if solapados:
                raise BloqueoSolapadoError(
                    f"Ya existe un bloqueo en el sillón {sillon_id} que solapa con el intervalo solicitado"
                )

        # 2. Salvaguarda RP-07: verificar que no existan turnos activos en el sillón
        turnos_activos = self._repositorio.buscar_activos_por_sillon(
            sillon_id=sillon_id,
            fecha_hora_inicio=f_inicio,
            fecha_hora_fin=f_fin,
        )
        if turnos_activos:
            raise ConflictoTurnosExistentesError(
                f"No se puede bloquear el sillón {sillon_id} porque existen turnos activos en el intervalo solicitado"
            )

        if self._puerto_bloqueos is None:
            raise ValueError("PuertoBloqueos no disponible en el servicio")

        nuevo_bloqueo = BloqueoSillon(
            tenant_id=tenant_id,
            sillon_id=sillon_id,
            fecha_hora_inicio=f_inicio,
            fecha_hora_fin=f_fin,
            motivo=motivo,
            creado_por=creado_por,
        )
        return self._puerto_bloqueos.guardar(nuevo_bloqueo)

    def listar_bloqueos(
        self,
        sillon_id: int | None = None,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
    ) -> list[BloqueoSillon]:
        """Consulta bloqueos del tenant."""
        if self._puerto_bloqueos is None:
            return []
        return self._puerto_bloqueos.listar(
            sillon_id=sillon_id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        )

    def eliminar_bloqueo(self, bloqueo_id: int) -> None:
        """Elimina un bloqueo existente o lanza BloqueoNoEncontradoError."""
        if self._puerto_bloqueos is None:
            raise BloqueoNoEncontradoError(f"El bloqueo {bloqueo_id} no existe")
        bloqueo = self._puerto_bloqueos.obtener_por_id(bloqueo_id)
        if bloqueo is None:
            raise BloqueoNoEncontradoError(f"El bloqueo {bloqueo_id} no existe")
        self._puerto_bloqueos.eliminar(bloqueo_id)

    def turnos_registrados(
        self,
        fecha: str | None = None,
        profesional_id: int | None = None,
        sillon_id: int | None = None,
    ) -> list[Turno]:
        """Devuelve una copia de la lista de turnos registrados con filtros opcionales."""
        if fecha is None and profesional_id is None and sillon_id is None:
            return self._repositorio.listar()
        return self._repositorio.listar(
            fecha=fecha,
            profesional_id=profesional_id,
            sillon_id=sillon_id,
        )

    def obtener_por_id(self, turno_id: int) -> Turno | None:
        """Recupera un turno por su identificador único."""
        return self._repositorio.obtener_por_id(turno_id)

    def _transicionar(self, turno: Turno, accion: str) -> Turno:
        """Aplica una acción de la lista blanca `_TRANSICIONES` y reemplaza el turno registrado.

        Devuelve la instancia actualizada (design D5); la referencia previa queda
        como snapshot del estado anterior.
        """
        destino = _TRANSICIONES.get((turno.estado, accion))
        if destino is None:
            raise TransicionInvalidaError(
                f"No se puede aplicar '{accion}' sobre un turno en estado "
                f"'{turno.estado}'"
            )
        actualizado = replace(turno, estado=destino)
        return self._repositorio.actualizar(actualizado)

    def confirmar(self, turno: Turno) -> Turno:
        """PENDIENTE → CONFIRMADO (RN-03)."""
        return self._transicionar(turno, "confirmar")

    def cancelar(self, turno: Turno) -> Turno:
        """PENDIENTE | CONFIRMADO → CANCELADO (RN-03). Libera profesional y sillón.

        Detección proactiva de lista de espera (RN-04, PA-14): busca el primer paciente prioritario
        y despacha una notificación de vacante sin bloquear la operación si falla.
        """
        turno_cancelado = self._transicionar(turno, "cancelar")

        if self._servicio_lista_espera is not None:
            try:
                prof_nombre = turno.profesional.nombre if turno.profesional else None
                candidatos = self._servicio_lista_espera.buscar_candidatos(
                    fecha=turno.fecha,
                    profesional_nombre=prof_nombre,
                )
                if candidatos:
                    prioritario = candidatos[0]
                    if self._servicio_notificaciones is not None:
                        self._servicio_notificaciones.notificar_vacante_disponible(
                            paciente=prioritario.paciente_nombre,
                            telefono=prioritario.paciente_telefono,
                            profesional=turno.profesional.nombre if turno.profesional else "el profesional",
                            fecha=turno.fecha,
                            hora_inicio=turno.hora_inicio,
                            turno_id=turno.id,
                        )
                    if prioritario.id is not None:
                        self._servicio_lista_espera.marcar_notificado(prioritario.id)
            except Exception as err:
                logger.error(
                    "Error no bloqueante al gestionar lista de espera tras cancelación de turno: %s",
                    err,
                    exc_info=True,
                )

        return turno_cancelado

    def completar(self, turno: Turno) -> Turno:
        """CONFIRMADO → COMPLETADO (RN-03)."""
        return self._transicionar(turno, "completar")

