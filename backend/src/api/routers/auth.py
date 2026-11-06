"""Router de autenticación y perfil de usuario (C-04, task 3.2)."""

from datetime import timedelta
from fastapi import APIRouter, Depends, Request

from src.api.dependencias import ContextoUsuario, obtener_usuario_actual
from src.api.errores import ErrorCredencialesInvalidas
from src.api.esquemas import LoginSolicitud, TokenRespuesta, UsuarioPerfilRespuesta
from src.api.seguridad import crear_token_acceso, verificar_password
from src.infrastructure.config import expiracion_token_minutos
from src.infrastructure.database import abrir_conexion
from src.repositories.usuarios_sqlite import RepositorioUsuariosSqlite

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenRespuesta)
def login(solicitud: LoginSolicitud, request: Request) -> TokenRespuesta:
    """Autentica a un usuario y genera su token JWT con claims de rol y tenant."""
    conexion = abrir_conexion(request.app.state.ruta_db)
    try:
        repo = RepositorioUsuariosSqlite(conexion)
        tenant_id = solicitud.tenant_id
        if tenant_id is None and hasattr(request.app.state, "tenant_por_defecto"):
            tenant_id = request.app.state.tenant_por_defecto

        usuario = repo.buscar_por_email(solicitud.email, tenant_id=tenant_id)
        if usuario is None or not usuario.activo:
            raise ErrorCredencialesInvalidas("Credenciales inválidas")

        if not verificar_password(solicitud.password, usuario.password_hash):
            raise ErrorCredencialesInvalidas("Credenciales inválidas")

        minutos = expiracion_token_minutos()
        claims = {
            "sub": str(usuario.id),
            "email": usuario.email,
            "tenant_id": usuario.tenant_id,
            "rol": usuario.rol,
            "profesional_id": usuario.profesional_id,
        }
        token = crear_token_acceso(claims, duracion=timedelta(minutes=minutos))
        return TokenRespuesta(
            access_token=token,
            token_type="bearer",
            expires_in=minutos * 60,
        )
    finally:
        conexion.close()


@router.get("/me", response_model=UsuarioPerfilRespuesta)
def obtener_perfil(
    usuario: ContextoUsuario = Depends(obtener_usuario_actual),
) -> UsuarioPerfilRespuesta:
    """Retorna los datos del usuario autenticado actual."""
    return UsuarioPerfilRespuesta(
        id=usuario.id,
        email=usuario.email,
        tenant_id=usuario.tenant_id,
        rol=usuario.rol,
        profesional_id=usuario.profesional_id,
    )

