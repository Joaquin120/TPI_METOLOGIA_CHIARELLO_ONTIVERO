import React from 'react';
import { useAuth } from '../context/AuthContext';

export const Navbar: React.FC = () => {
  const { usuario, cerrarSesion } = useAuth();

  const getRolBadgeClass = (rol?: string) => {
    switch (rol) {
      case 'Administrador':
        return 'badge badge-admin';
      case 'Recepcionista':
        return 'badge badge-recep';
      case 'Profesional':
        return 'badge badge-prof';
      default:
        return 'badge';
    }
  };

  return (
    <header className="navbar" data-testid="navbar">
      <div className="navbar-brand">
        <span className="brand-icon">🦷</span>
        <span className="brand-name">Consultorio Odontológico</span>
        <span className="tenant-tag">Clínica #{usuario?.tenant_id ?? 1}</span>
      </div>

      <div className="navbar-user">
        {usuario && (
          <div className="user-info">
            <span className="user-name" data-testid="user-name">
              {usuario.nombre || usuario.email}
            </span>
            <span className={getRolBadgeClass(usuario.rol)} data-testid="user-role">
              {usuario.rol}
            </span>
          </div>
        )}
        <button
          onClick={cerrarSesion}
          className="btn btn-outline btn-sm"
          data-testid="btn-logout"
          title="Cerrar Sesión"
        >
          Cerrar Sesión
        </button>
      </div>
    </header>
  );
};
