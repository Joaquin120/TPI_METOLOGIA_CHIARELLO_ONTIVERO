import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AppRoutes } from '../src/App';
import { AuthProvider } from '../src/context/AuthContext';
import * as authApi from '../src/api/auth';
import { Usuario } from '../src/types';

describe('App Routing e Integración de Flujo', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('intento de navegar a ruta protegida sin sesión redirige a /login', () => {
    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/agenda']}>
          <AppRoutes />
        </MemoryRouter>
      </AuthProvider>
    );

    expect(screen.getByTestId('login-container')).toBeInTheDocument();
    expect(screen.getByTestId('input-email')).toBeInTheDocument();
    expect(screen.queryByTestId('page-agenda')).not.toBeInTheDocument();
  });

  it('formulario de login muestra error ante credenciales incorrectas', async () => {
    vi.spyOn(authApi, 'login').mockRejectedValue(
      new Error('Credenciales inválidas')
    );

    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/login']}>
          <AppRoutes />
        </MemoryRouter>
      </AuthProvider>
    );

    fireEvent.change(screen.getByTestId('input-email'), {
      target: { value: 'invalido@clinica.com' },
    });
    fireEvent.change(screen.getByTestId('input-password'), {
      target: { value: 'erronea' },
    });

    fireEvent.click(screen.getByTestId('btn-login'));

    await waitFor(() => {
      expect(screen.getByTestId('login-error')).toBeInTheDocument();
      expect(screen.getByTestId('login-error')).toHaveTextContent('Credenciales inválidas');
    });

    // Permanece en /login
    expect(screen.getByTestId('login-container')).toBeInTheDocument();
  });

  it('formulario de login autentica y redirige a /agenda', async () => {
    const usuarioMock: Usuario = {
      id: 2,
      email: 'recep@clinica.com',
      rol: 'Recepcionista',
      tenant_id: 1,
      nombre: 'Recepcionista Turnos',
    };

    vi.spyOn(authApi, 'login').mockResolvedValue({
      access_token: 'valid-jwt-token',
      token_type: 'bearer',
      usuario: usuarioMock,
    });

    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/login']}>
          <AppRoutes />
        </MemoryRouter>
      </AuthProvider>
    );

    fireEvent.change(screen.getByTestId('input-email'), {
      target: { value: 'recep@clinica.com' },
    });
    fireEvent.change(screen.getByTestId('input-password'), {
      target: { value: 'correcto123' },
    });

    fireEvent.click(screen.getByTestId('btn-login'));

    await waitFor(() => {
      expect(screen.getByTestId('page-agenda')).toBeInTheDocument();
      expect(screen.getByText('Agenda de Turnos')).toBeInTheDocument();
    });
  });

  it('bloquea acceso a /auditoria para rol Recepcionista mostrando Acceso Denegado', () => {
    const usuarioRecep: Usuario = {
      id: 3,
      email: 'recep2@clinica.com',
      rol: 'Recepcionista',
      tenant_id: 1,
      nombre: 'Recepción 2',
    };
    localStorage.setItem('token', 'token-recep');
    localStorage.setItem('usuario', JSON.stringify(usuarioRecep));

    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/auditoria']}>
          <AppRoutes />
        </MemoryRouter>
      </AuthProvider>
    );

    expect(screen.getByTestId('acceso-denegado')).toBeInTheDocument();
    expect(screen.getByText('Acceso Denegado')).toBeInTheDocument();
    expect(screen.queryByTestId('page-auditoria')).not.toBeInTheDocument();
  });
});
