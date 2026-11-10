"""Excepciones de dominio explícitas para la gestión de turnos."""


class SolapamientoProfesionalError(Exception):
    """El profesional ya tiene un turno asignado que colisiona en horario."""

    def __init__(self, mensaje: str = "El profesional ya tiene un turno en ese horario") -> None:
        super().__init__(mensaje)


class SolapamientoSillonError(Exception):
    """El sillón/box ya está ocupado en ese rango horario."""

    def __init__(self, mensaje: str = "El sillón ya está ocupado en ese horario") -> None:
        super().__init__(mensaje)


class TransicionInvalidaError(Exception):
    """La transición solicitada no está permitida para el estado actual del turno."""

    def __init__(self, mensaje: str = "La transición no es válida para el estado del turno") -> None:
        super().__init__(mensaje)


class RecursoDuplicadoError(Exception):
    """Ya existe un recurso clínico con el mismo identificador o nombre en el tenant."""

    def __init__(self, mensaje: str = "Ya existe un recurso con ese nombre en esta clínica") -> None:
        super().__init__(mensaje)


class SillonBloqueadoError(Exception):
    """El sillón se encuentra bloqueado por mantenimiento en el intervalo solicitado."""

    def __init__(self, mensaje: str = "El sillón se encuentra bloqueado por mantenimiento") -> None:
        super().__init__(mensaje)


class ConflictoTurnosExistentesError(Exception):
    """No se puede bloquear el sillón porque existen turnos activos en el intervalo solicitado (RP-07)."""

    def __init__(self, mensaje: str = "Existen turnos activos en el intervalo del bloqueo solicitado") -> None:
        super().__init__(mensaje)


class BloqueoSolapadoError(Exception):
    """Ya existe otro bloqueo registrado en ese sillón que se solapa con el intervalo solicitado."""

    def __init__(self, mensaje: str = "Ya existe un bloqueo en ese sillón para el intervalo solicitado") -> None:
        super().__init__(mensaje)


class BloqueoNoEncontradoError(Exception):
    """El bloqueo solicitado no existe en el tenant."""

    def __init__(self, mensaje: str = "Bloqueo no encontrado") -> None:
        super().__init__(mensaje)

