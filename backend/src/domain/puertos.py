"""Puertos de persistencia del dominio (design D1, DIP).

Contratos abstractos basados en `typing.Protocol`.
El dominio no importa `sqlite3` ni conoce SQL ni detalles de infraestructura.
"""

from typing import Protocol, runtime_checkable

from src.domain.models import (
    BloqueoSillon,
    EntradaListaEspera,
    MensajeWhatsApp,
    Profesional,
    ResultadoEnvio,
    Sillon,
    Turno,
)


@runtime_checkable
class PuertoTurnos(Protocol):
    """Puerto de persistencia para la gestión de turnos."""

    def guardar(self, turno: Turno) -> Turno:
        """Persiste un nuevo turno y devuelve la entidad con su identificador."""
        ...

    def actualizar(self, turno: Turno) -> Turno:
        """Actualiza el estado de un turno persistido existente."""
        ...

    def actualizar_reprogramacion(self, turno: Turno) -> Turno:
        """Actualiza fecha, horario y recursos de un turno existente."""
        ...

    def obtener_por_id(self, turno_id: int) -> Turno | None:
        """Recupera un turno por su identificador en el contexto actual."""
        ...

    def listar(
        self,
        fecha: str | None = None,
        profesional_id: int | None = None,
        sillon_id: int | None = None,
    ) -> list[Turno]:
        """Recupera la lista de turnos registrados aplicando filtros opcionales."""
        ...

    def agregar(self, turno: Turno) -> None:
        """Siembra directamente un turno (usado por helpers de prueba)."""
        ...

    def buscar_activos_solapables(
        self,
        fecha: str,
        hora_inicio: str,
        hora_fin: str,
        profesional: Profesional,
        sillon: Sillon,
        excluir_turno_id: int | None = None,
    ) -> list[Turno]:
        """Devuelve turnos activos que solapan temporalmente con el intervalo dado."""
        ...

    def buscar_activos_por_sillon(
        self,
        sillon_id: int,
        fecha_hora_inicio: str,
        fecha_hora_fin: str,
    ) -> list[Turno]:
        """Devuelve turnos activos asignados al sillón en el intervalo dado (RP-07)."""
        ...


@runtime_checkable
class PuertoBloqueos(Protocol):
    """Puerto de persistencia para la gestión de bloqueos de sillones."""

    def guardar(self, bloqueo: BloqueoSillon) -> BloqueoSillon:
        """Persiste un nuevo bloqueo y devuelve la entidad con su identificador."""
        ...

    def buscar_bloqueos_solapados(
        self,
        sillon_id: int,
        fecha_hora_inicio: str,
        fecha_hora_fin: str,
        excluir_bloqueo_id: int | None = None,
    ) -> list[BloqueoSillon]:
        """Devuelve bloqueos del sillón que solapan temporalmente con el intervalo dado."""
        ...

    def listar(
        self,
        sillon_id: int | None = None,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
    ) -> list[BloqueoSillon]:
        """Recupera la lista de bloqueos registrados aplicando filtros opcionales."""
        ...

    def obtener_por_id(self, bloqueo_id: int) -> BloqueoSillon | None:
        """Recupera un bloqueo por su identificador único dentro del tenant."""
        ...

    def eliminar(self, bloqueo_id: int) -> bool:
        """Elimina un bloqueo por su identificador. Retorna True si existía y fue eliminado."""
        ...


@runtime_checkable
class ProveedorWhatsApp(Protocol):
    """Puerto para el despacho de mensajes a través de WhatsApp (C-14, DP-09)."""

    def enviar_mensaje(self, mensaje: MensajeWhatsApp) -> ResultadoEnvio:
        """Despacha un mensaje por WhatsApp devolviendo el resultado del envío."""
        ...


@runtime_checkable
class PuertoListaEspera(Protocol):
    """Puerto de persistencia para la gestión de lista de espera (C-15, F-08)."""

    def guardar(self, entrada: EntradaListaEspera) -> EntradaListaEspera:
        """Persiste una nueva entrada en lista de espera."""
        ...

    def actualizar(self, entrada: EntradaListaEspera) -> EntradaListaEspera:
        """Actualiza el estado u observaciones de una entrada existente."""
        ...

    def obtener_por_id(self, entrada_id: int) -> EntradaListaEspera | None:
        """Recupera una entrada por su identificador único dentro del tenant."""
        ...

    def listar(
        self,
        fecha: str | None = None,
        profesional_nombre: str | None = None,
        estado: str | None = None,
    ) -> list[EntradaListaEspera]:
        """Recupera la lista de entradas aplicando filtros opcionales."""
        ...

    def buscar_candidatos(
        self, fecha: str, profesional_nombre: str | None = None
    ) -> list[EntradaListaEspera]:
        """Recupera candidatos pendientes priorizados por orden cronológico (FIFO)."""
        ...


