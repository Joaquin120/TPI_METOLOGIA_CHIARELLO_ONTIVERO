import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { AuthProvider, useAuth } from '../src/context/AuthContext';
import * as authApi from '../src/api/auth';
import { Usuario } from '../src/types';

const ComponentePrueba: React.FC = () => {
  const { usuario, token, estaAutenticado, iniciarSesion, cerrarSesion } = useAuth();

  return (
    <div>
      <span data-testid="autenticado">{estaAutenticado ? 'SI' : 'NO'}</span>
      <span data-testid="usuario-email">{usuario?.email || 'ninguno'}</span>
      <span data-testid="usuario-rol">{usuario?.rol || 'ninguno'}</span>
      <span data-testid="token-val">{token || 'sin-token'}</span>
      <button
        data-testid="btn-login-test"
        onClick={() => iniciarSesion({ email: 'admin@clinica.com', password: 'secret' })}
      >
        Login
      </button>
      <button data-testid="btn-logout-test" onClick={cerrarSesion}>
        Logout
      </button>
    </div>
  );
};

describe('AuthContext', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('inicia en estado no autenticado cuando el almacenamiento está vacío', () => {
    render(
      <AuthProvider>
        <ComponentePrueba />
      </AuthProvider>
    );

    expect(screen.getByTestId('autenticado')).toHaveTextContent('NO');
    expect(screen.getByTestId('usuario-email')).toHaveTextContent('ninguno');
    expect(screen.getByTestId('token-val')).toHaveTextContent('sin-token');
  });

  it('restaura sesión activa si existen token y usuario en localStorage', () => {
    const usuarioGuardado: Usuario = {
      id: 2,
      email: 'recep@clinica.com',
      rol: 'Recepcionista',
      tenant_id: 1,
      nombre: 'Recepción',
    };
    localStorage.setItem('token', 'token-previo-abc');
    localStorage.setItem('usuario', JSON.stringify(usuarioGuardado));

    render(
      <AuthProvider>
        <ComponentePrueba />
      </AuthProvider>
    );

    expect(screen.getByTestId('autenticado')).toHaveTextContent('SI');
    expect(screen.getByTestId('usuario-email')).toHaveTextContent('recep@clinica.com');
    expect(screen.getByTestId('usuario-rol')).toHaveTextContent('Recepcionista');
    expect(screen.getByTestId('token-val')).toHaveTextContent('token-previo-abc');
  });

  it('inicia sesión exitosamente y persiste token y usuario', async () => {
    const usuarioMock: Usuario = {
      id: 1,
      email: 'admin@clinica.com',
      rol: 'Administrador',
      tenant_id: 1,
      nombre: 'Administrador',
    };

    vi.spyOn(authApi, 'login').mockResolvedValue({
      access_token: 'nuevo-jwt-token-xyz',
      token_type: 'bearer',
      usuario: usuarioMock,
    });

    render(
      <AuthProvider>
        <ComponentePrueba />
      </AuthProvider>
    );

    await act(async () => {
      screen.getByTestId('btn-login-test').click();
    });

    expect(screen.getByTestId('autenticado')).toHaveTextContent('SI');
    expect(screen.getByTestId('usuario-email')).toHaveTextContent('admin@clinica.com');
    expect(screen.getByTestId('usuario-rol')).toHaveTextContent('Administrador');
    expect(localStorage.getItem('token')).toBe('nuevo-jwt-token-xyz');
    expect(JSON.parse(localStorage.getItem('usuario') || '{}').email).toBe('admin@clinica.com');
  });

  it('cierra sesión, purga almacenamiento y actualiza el estado', async () => {
    localStorage.setItem('token', 'jwt-activo');
    localStorage.setItem(
      'usuario',
      JSON.stringify({ id: 1, email: 'admin@clinica.com', rol: 'Administrador', tenant_id: 1 })
    );

    render(
      <AuthProvider>
        <ComponentePrueba />
      </AuthProvider>
    );

    expect(screen.getByTestId('autenticado')).toHaveTextContent('SI');

    act(() => {
      screen.getByTestId('btn-logout-test').click();
    });

    expect(screen.getByTestId('autenticado')).toHaveTextContent('NO');
    expect(localStorage.getItem('token')).toBeNull();
    expect(localStorage.getItem('usuario')).toBeNull();
  });
});
