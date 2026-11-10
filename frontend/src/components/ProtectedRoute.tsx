import React, { ReactNode } from 'react';
import { Navigate, useLocation, Link, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Rol } from '../types';
import { Layout } from './Layout';

interface ProtectedRouteProps {
  rolesPermitidos?: Rol[];
  children?: ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ rolesPermitidos, children }) => {
  const { estaAutenticado, usuario, cargando } = useAuth();
  const location = useLocation();

  if (cargando) {
    return (
      <div className="layout-loading" data-testid="loading-state">
        <div className="spinner"></div>
        <p>Cargando sesión...</p>
      </div>
    );
  }

  if (!estaAutenticado || !usuario) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (rolesPermitidos && !rolesPermitidos.includes(usuario.rol)) {
    return (
      <Layout>
        <div className="acceso-denegado" data-testid="acceso-denegado">
          <div className="card-error">
            <h2>Acceso Denegado</h2>
            <p>No tienes permisos suficientes para acceder a esta sección.</p>
            <p className="texto-secundario">
              Tu rol actual es: <strong>{usuario.rol}</strong>
            </p>
            <Link to="/agenda" className="btn btn-primary" data-testid="btn-volver-agenda">
              Volver a la Agenda
            </Link>
          </div>
        </div>
      </Layout>
    );
  }

  return <Layout>{children ? children : <Outlet />}</Layout>;
};
