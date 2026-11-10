import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { AuthContext, AuthContextType } from '../src/context/AuthContext';
import { ProtectedRoute } from '../src/components/ProtectedRoute';
import { Usuario } from '../src/types';

const crearContexto = (valores: Partial<AuthContextType> = {}): AuthContextType => ({
  usuario: null,
  token: null,
  estaAutenticado: false,
  cargando: false,
  iniciarSesion: async () => {},
  cerrarSesion: () => {},
  ...valores,
});

describe('ProtectedRoute', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('redirige a /login si el usuario no está autenticado', () => {
    const contexto = crearContexto({ estaAutenticado: false, usuario: null });

    render(
      <AuthContext.Provider value={contexto}>
        <MemoryRouter initialEntries={['/agenda']}>
          <Routes>
            <Route path="/login" element={<div>Pantalla de Login</div>} />
            <Route
              path="/agenda"
              element={
                <ProtectedRoute>
                  <div>Contenido Protegido</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    );

    expect(screen.getByText('Pantalla de Login')).toBeInTheDocument();
    expect(screen.queryByText('Contenido Protegido')).not.toBeInTheDocument();
  });

  it('muestra aviso de Acceso Denegado si el rol del usuario no está autorizado', () => {
    const usuarioProf: Usuario = {
      id: 5,
      email: 'doctor@clinica.com',
      rol: 'Profesional',
      tenant_id: 1,
      nombre: 'Dr. Ejemplo',
    };

    const contexto = crearContexto({
      estaAutenticado: true,
      token: 'jwt-valido',
      usuario: usuarioProf,
    });

    render(
      <AuthContext.Provider value={contexto}>
        <MemoryRouter initialEntries={['/auditoria']}>
          <Routes>
            <Route
              path="/auditoria"
              element={
                <ProtectedRoute rolesPermitidos={['Administrador']}>
                  <div>Sección Secreta de Auditoría</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    );

    expect(screen.getByTestId('acceso-denegado')).toBeInTheDocument();
    expect(screen.getByText(/Acceso Denegado/i)).toBeInTheDocument();
    expect(screen.getByText(/Tu rol actual es:/i)).toHaveTextContent('Profesional');
    expect(screen.queryByText('Sección Secreta de Auditoría')).not.toBeInTheDocument();
  });

  it('permite el acceso si el usuario está autenticado y tiene rol autorizado', () => {
    const usuarioAdmin: Usuario = {
      id: 1,
      email: 'admin@clinica.com',
      rol: 'Administrador',
      tenant_id: 1,
    };

    const contexto = crearContexto({
      estaAutenticado: true,
      token: 'jwt-valido',
      usuario: usuarioAdmin,
    });

    render(
      <AuthContext.Provider value={contexto}>
        <MemoryRouter initialEntries={['/auditoria']}>
          <Routes>
            <Route
              path="/auditoria"
              element={
                <ProtectedRoute rolesPermitidos={['Administrador']}>
                  <div data-testid="contenido-autorizado">Vista de Auditoría Permitida</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    );

    expect(screen.getByTestId('contenido-autorizado')).toBeInTheDocument();
    expect(screen.queryByTestId('acceso-denegado')).not.toBeInTheDocument();
  });
});
