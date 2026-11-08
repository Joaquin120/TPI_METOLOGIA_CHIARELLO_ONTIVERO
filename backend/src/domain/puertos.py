"""Puertos de persistencia del dominio (design D1, DIP).

Contratos abstractos basados en `typing.Protocol`.
El dominio no importa `sqlite3` ni conoce SQL ni detalles de infraestructura.
"""

from typing import Protocol, runtime_checkable

from src.domain.models import Profesional, Sillon, Turno


@runtime_checkable
class PuertoTurnos(Protocol):
    """Puerto de persistencia para la gestión de turnos."""

    def guardar(self, turno: Turno) -> Turno:
        """Persiste un nuevo turno y devuelve la entidad con su identificador."""
        ...

    def actualizar(self, turno: Turno) -> Turno:
        """Actualiza el estado de un turno persistido existente."""
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
    ) -> list[Turno]:
        """Devuelve turnos activos que solapan temporalmente con el intervalo dado."""
        ...
