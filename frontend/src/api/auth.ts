import { clienteApi } from './cliente';
import { Credenciales, LoginRespuesta, TokenRespuesta, Usuario, Rol } from '../types';

export function decodificarJwtPayload(token: string): Partial<Usuario> | null {
  try {
    const partes = token.split('.');
    if (partes.length < 2) return null;
    const base64 = partes[1].replace(/-/g, '+').replace(/_/g, '/');
    const jsonStr = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    const claims = JSON.parse(jsonStr);
    return {
      id: Number(claims.sub ?? claims.id ?? 1),
      email: claims.email ?? '',
      rol: (claims.rol as Rol) ?? 'Recepcionista',
      tenant_id: Number(claims.tenant_id ?? 1),
      profesional_id: claims.profesional_id !== undefined ? Number(claims.profesional_id) : null,
      nombre: claims.email ? claims.email.split('@')[0] : 'Usuario',
    };
  } catch {
    return null;
  }
}

export async function login(credenciales: Credenciales): Promise<LoginRespuesta> {
  const tokenRespuesta = await clienteApi.post<TokenRespuesta>('/auth/login', credenciales);
  clienteApi.setToken(tokenRespuesta.access_token);

  let usuario: Usuario;
  try {
    usuario = await obtenerPerfil();
  } catch {
    const decoded = decodificarJwtPayload(tokenRespuesta.access_token);
    usuario = {
      id: decoded?.id ?? 1,
      email: credenciales.email,
      rol: (decoded?.rol as Rol) ?? 'Recepcionista',
      tenant_id: decoded?.tenant_id ?? 1,
      nombre: credenciales.email.split('@')[0],
      profesional_id: decoded?.profesional_id ?? null,
    };
  }

  if (!usuario.nombre) {
    usuario.nombre = usuario.email.split('@')[0];
  }

  return {
    access_token: tokenRespuesta.access_token,
    token_type: tokenRespuesta.token_type,
    expires_in: tokenRespuesta.expires_in,
    usuario,
  };
}

export async function obtenerPerfil(): Promise<Usuario> {
  const perfil = await clienteApi.get<Usuario>('/auth/me');
  if (!perfil.nombre && perfil.email) {
    perfil.nombre = perfil.email.split('@')[0];
  }
  return perfil;
}
