import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AuthContext, AuthContextType } from '../src/context/AuthContext';
import { Layout } from '../src/components/Layout';
import { Usuario } from '../src/types';

const renderConRol = (rol: 'Administrador' | 'Recepcionista' | 'Profesional', onLogout = vi.fn()) => {
  const usuario: Usuario = {
    id: 10,
    email: `${rol.toLowerCase()}@clinica.com`,
    rol,
    tenant_id: 1,
    nombre: `Usuario ${rol}`,
  };

  const contexto: AuthContextType = {
    usuario,
    token: 'jwt-123',
    estaAutenticado: true,
    cargando: false,
    iniciarSesion: async () => {},
    cerrarSesion: onLogout,
  };

  return render(
    <AuthContext.Provider value={contexto}>
      <MemoryRouter>
        <Layout>
          <div data-testid="hijo-layout">Contenido Interno</div>
        </Layout>
      </MemoryRouter>
    </AuthContext.Provider>
  );
};

describe('Layout y Navegación Contextual', () => {
  it('renderiza barra de navegación con datos de usuario y botón de cerrar sesión', () => {
    const onLogout = vi.fn();
    renderConRol('Administrador', onLogout);

    expect(screen.getByTestId('navbar')).toBeInTheDocument();
    expect(screen.getByTestId('user-name')).toHaveTextContent('Usuario Administrador');
    expect(screen.getByTestId('user-role')).toHaveTextContent('Administrador');

    const btnLogout = screen.getByTestId('btn-logout');
    fireEvent.click(btnLogout);
    expect(onLogout).toHaveBeenCalledTimes(1);
  });

  it('muestra navegación completa para rol Administrador (Agenda, Pacientes, Recursos, Auditoría)', () => {
    renderConRol('Administrador');

    expect(screen.getByTestId('nav-link-agenda')).toBeInTheDocument();
    expect(screen.getByTestId('nav-link-pacientes')).toBeInTheDocument();
    expect(screen.getByTestId('nav-link-recursos')).toBeInTheDocument();
    expect(screen.getByTestId('nav-link-auditoría')).toBeInTheDocument();
  });

  it('muestra navegación restringida para rol Recepcionista (excluye Auditoría)', () => {
    renderConRol('Recepcionista');

    expect(screen.getByTestId('nav-link-agenda')).toBeInTheDocument();
    expect(screen.getByTestId('nav-link-pacientes')).toBeInTheDocument();
    expect(screen.getByTestId('nav-link-recursos')).toBeInTheDocument();
    expect(screen.queryByTestId('nav-link-auditoría')).not.toBeInTheDocument();
  });

  it('muestra únicamente la Agenda para rol Profesional', () => {
    renderConRol('Profesional');

    expect(screen.getByTestId('nav-link-agenda')).toBeInTheDocument();
    expect(screen.queryByTestId('nav-link-pacientes')).not.toBeInTheDocument();
    expect(screen.queryByTestId('nav-link-recursos')).not.toBeInTheDocument();
    expect(screen.queryByTestId('nav-link-auditoría')).not.toBeInTheDocument();
  });
});
