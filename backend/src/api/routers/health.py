"""Health check sin contexto de tenant (design D5).

No depende de la base de negocio: solo confirma que la app responde.
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Disponibilidad del servicio; no resuelve tenant ni consulta turnos."""
    return {"status": "ok"}
