import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { Usuario, Credenciales } from '../types';
import { clienteApi } from '../api/cliente';
import { login as apiLogin } from '../api/auth';

export interface AuthContextType {
  usuario: Usuario | null;
  token: string | null;
  estaAutenticado: boolean;
  cargando: boolean;
  iniciarSesion: (credenciales: Credenciales) => Promise<void>;
  cerrarSesion: () => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [token, setTokenState] = useState<string | null>(() => {
    if (typeof localStorage !== 'undefined') {
      return localStorage.getItem('token');
    }
    return null;
  });

  const [usuario, setUsuario] = useState<Usuario | null>(() => {
    if (typeof localStorage !== 'undefined') {
      const u = localStorage.getItem('usuario');
      if (u) {
        try {
          return JSON.parse(u);
        } catch {
          return null;
        }
      }
    }
    return null;
  });

  const [cargando, setCargando] = useState<boolean>(false);

  const cerrarSesion = useCallback(() => {
    setTokenState(null);
    setUsuario(null);
    clienteApi.setToken(null);
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem('usuario');
    }
  }, []);

  useEffect(() => {
    clienteApi.setOnUnauthorized(() => {
      cerrarSesion();
    });
  }, [cerrarSesion]);

  const iniciarSesion = async (credenciales: Credenciales): Promise<void> => {
    setCargando(true);
    try {
      const respuesta = await apiLogin(credenciales);
      setTokenState(respuesta.access_token);
      clienteApi.setToken(respuesta.access_token);
      setUsuario(respuesta.usuario);
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem('token', respuesta.access_token);
        localStorage.setItem('usuario', JSON.stringify(respuesta.usuario));
      }
    } finally {
      setCargando(false);
    }
  };

  const valor: AuthContextType = {
    usuario,
    token,
    estaAutenticado: Boolean(token && usuario),
    cargando,
    iniciarSesion,
    cerrarSesion,
  };

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>;
};

export function useAuth(): AuthContextType {
  const contexto = useContext(AuthContext);
  if (!contexto) {
    throw new Error('useAuth debe ser utilizado dentro de un AuthProvider');
  }
  return contexto;
}
