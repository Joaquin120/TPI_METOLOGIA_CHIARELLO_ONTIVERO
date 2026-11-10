import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Rol } from '../types';

export const Sidebar: React.FC = () => {
  const { usuario } = useAuth();
  const rol = usuario?.rol as Rol | undefined;

  const getLinksPorRol = () => {
    const links = [{ to: '/agenda', label: 'Agenda', icon: '📅' }];

    if (rol === 'Administrador' || rol === 'Recepcionista') {
      links.push(
        { to: '/pacientes', label: 'Pacientes', icon: '👥' },
        { to: '/recursos', label: 'Recursos', icon: '🪑' }
      );
    }

    if (rol === 'Administrador') {
      links.push({ to: '/auditoria', label: 'Auditoría', icon: '📋' });
    }

    return links;
  };

  const navLinks = getLinksPorRol();

  return (
    <aside className="sidebar" data-testid="sidebar">
      <nav className="sidebar-nav">
        <ul>
          {navLinks.map((link) => (
            <li key={link.to}>
              <NavLink
                to={link.to}
                className={({ isActive }) =>
                  isActive ? 'sidebar-link active' : 'sidebar-link'
                }
                data-testid={`nav-link-${link.label.toLowerCase()}`}
              >
                <span className="sidebar-icon">{link.icon}</span>
                <span className="sidebar-label">{link.label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  );
};
