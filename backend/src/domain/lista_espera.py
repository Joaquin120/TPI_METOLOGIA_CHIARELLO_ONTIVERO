"""Servicio de dominio para la gestión de lista de espera (C-15, F-08, PA-14).

Cumple estrictamente con las reglas de pureza de dominio: sin dependencias de frameworks ni I/O.
"""

from dataclasses import replace

from src.domain.models import EntradaListaEspera, EstadoListaEspera
from src.domain.puertos import PuertoListaEspera


class ServicioListaEspera:
    """Orquesta el registro, consulta, cancelación y búsqueda de candidatos en lista de espera."""

    def __init__(self, puerto: PuertoListaEspera) -> None:
        self._puerto = puerto

    def registrar(
        self,
        paciente_nombre: str,
        paciente_telefono: str,
        fecha_deseada: str,
        motivo: str,
        profesional_nombre: str | None = None,
        franja_horaria: str | None = None,
    ) -> EntradaListaEspera:
        """Registra un paciente en lista de espera validando datos obligatorios."""
        nombre_limpio = paciente_nombre.strip() if paciente_nombre else ""
        if not nombre_limpio:
            raise ValueError("El nombre del paciente es obligatorio")

        telefono_limpio = paciente_telefono.strip() if paciente_telefono else ""
        if not telefono_limpio:
            raise ValueError("El teléfono del paciente es obligatorio")

        motivo_limpio = motivo.strip() if motivo else ""
        if not motivo_limpio:
            raise ValueError("El motivo es obligatorio")

        fecha_limpia = fecha_deseada.strip() if fecha_deseada else ""
        if not fecha_limpia:
            raise ValueError("La fecha deseada es obligatoria")

        entrada = EntradaListaEspera(
            paciente_nombre=nombre_limpio,
            paciente_telefono=telefono_limpio,
            fecha_deseada=fecha_limpia,
            motivo=motivo_limpio,
            profesional_nombre=profesional_nombre.strip() if profesional_nombre else None,
            franja_horaria=franja_horaria.strip() if franja_horaria else None,
            estado=EstadoListaEspera.PENDIENTE,
        )
        return self._puerto.guardar(entrada)

    def listar(
        self,
        fecha: str | None = None,
        profesional_nombre: str | None = None,
        estado: str | None = None,
    ) -> list[EntradaListaEspera]:
        """Obtiene entradas en lista de espera aplicando filtros opcionales."""
        return self._puerto.listar(
            fecha=fecha.strip() if fecha else None,
            profesional_nombre=profesional_nombre.strip() if profesional_nombre else None,
            estado=estado.strip() if estado else None,
        )

    def obtener_por_id(self, entrada_id: int) -> EntradaListaEspera | None:
        """Obtiene una entrada por su ID."""
        return self._puerto.obtener_por_id(entrada_id)

    def cancelar(self, entrada_id: int) -> EntradaListaEspera:
        """Cancela la solicitud de un paciente en lista de espera."""
        entrada = self._puerto.obtener_por_id(entrada_id)
        if entrada is None:
            raise ValueError("Entrada no encontrada")

        entrada_cancelada = replace(entrada, estado=EstadoListaEspera.CANCELADO)
        return self._puerto.actualizar(entrada_cancelada)

    def marcar_notificado(self, entrada_id: int) -> EntradaListaEspera:
        """Marca una entrada como notificada de vacante disponible."""
        entrada = self._puerto.obtener_por_id(entrada_id)
        if entrada is None:
            raise ValueError("Entrada no encontrada")

        entrada_notificada = replace(entrada, estado=EstadoListaEspera.NOTIFICADO)
        return self._puerto.actualizar(entrada_notificada)

    def marcar_asignado(self, entrada_id: int) -> EntradaListaEspera:
        """Marca una entrada como asignada a un turno definitivo."""
        entrada = self._puerto.obtener_por_id(entrada_id)
        if entrada is None:
            raise ValueError("Entrada no encontrada")

        entrada_asignada = replace(entrada, estado=EstadoListaEspera.ASIGNADO)
        return self._puerto.actualizar(entrada_asignada)

    def buscar_candidatos(
        self, fecha: str, profesional_nombre: str | None = None
    ) -> list[EntradaListaEspera]:
        """Recupera candidatos prioritarios para una vacante (FIFO, PA-14)."""
        return self._puerto.buscar_candidatos(
            fecha=fecha,
            profesional_nombre=profesional_nombre.strip() if profesional_nombre else None,
        )

