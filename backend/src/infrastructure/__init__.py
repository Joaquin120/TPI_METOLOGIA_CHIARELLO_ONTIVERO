"""Capa de infraestructura: conexión, migración, configuración y semilla (design D1/D4/D7).

Este paquete es el círculo externo: contiene `sqlite3` y SQL, y el dominio
jamás lo importa (clean architecture: la dependencia apunta hacia adentro).
"""
