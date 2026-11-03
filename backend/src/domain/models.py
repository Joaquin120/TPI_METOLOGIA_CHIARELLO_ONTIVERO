"""Modelos de dominio para la gestión de turnos odontológicos."""

from dataclasses import dataclass

# Constantes de estado del turno (fuente de verdad de `Turno.estado`).
# Se usan como texto plano — no un Enum — para preservar la igualdad literal
# `turno.estado == "CONFIRMADO"` y la persistencia futura como texto (design D1).
PENDIENTE = "PENDIENTE"
CONFIRMADO = "CONFIRMADO"
CANCELADO = "CANCELADO"
COMPLETADO = "COMPLETADO"


@dataclass(frozen=True)
class Profesional:
    """Profesional de la salud que atiende turnos."""

    nombre: str


@dataclass(frozen=True)
class Sillon:
    """Sillón/box odontológico en el que se realiza la atención."""

    nombre: str


@dataclass(frozen=True)
class Turno:
    """Turno odontológico confirmado en un intervalo semiabierto [hora_inicio, hora_fin)."""

    profesional: Profesional
    sillon: Sillon
    fecha: str
    hora_inicio: str
    hora_fin: str
    paciente: str
    estado: str = CONFIRMADO
