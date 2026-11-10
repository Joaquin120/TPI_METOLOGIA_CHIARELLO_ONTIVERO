import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Login } from './pages/Login';
import { Agenda } from './pages/Agenda';
import { Pacientes } from './pages/Pacientes';
import { Recursos } from './pages/Recursos';
import { Auditoria } from './pages/Auditoria';

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Navigate to="/agenda" replace />} />

      {/* Agenda: Administrador, Recepcionista y Profesional */}
      <Route
        path="/agenda"
        element={
          <ProtectedRoute rolesPermitidos={['Administrador', 'Recepcionista', 'Profesional']}>
            <Agenda />
          </ProtectedRoute>
        }
      />

      {/* Pacientes: Administrador y Recepcionista */}
      <Route
        path="/pacientes"
        element={
          <ProtectedRoute rolesPermitidos={['Administrador', 'Recepcionista']}>
            <Pacientes />
          </ProtectedRoute>
        }
      />

      {/* Recursos: Administrador y Recepcionista */}
      <Route
        path="/recursos"
        element={
          <ProtectedRoute rolesPermitidos={['Administrador', 'Recepcionista']}>
            <Recursos />
          </ProtectedRoute>
        }
      />

      {/* Auditoría: Solo Administrador */}
      <Route
        path="/auditoria"
        element={
          <ProtectedRoute rolesPermitidos={['Administrador']}>
            <Auditoria />
          </ProtectedRoute>
        }
      />

      {/* 404 Not Found */}
      <Route
        path="*"
        element={
          <div style={{ padding: '3rem', textAlign: 'center' }}>
            <h2>404 - Página no encontrada</h2>
            <p style={{ marginTop: '0.5rem', color: '#64748b' }}>
              La dirección solicitada no existe.
            </p>
          </div>
        }
      />
    </Routes>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
};
