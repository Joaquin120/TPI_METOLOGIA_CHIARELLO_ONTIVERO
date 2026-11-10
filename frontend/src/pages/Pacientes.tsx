import React from 'react';

export const Pacientes: React.FC = () => {
  return (
    <div className="page-pacientes" data-testid="page-pacientes">
      <div className="page-header">
        <h1>Gestión de Pacientes</h1>
        <p>Registro y consulta de pacientes con DNI sintético y datos de contacto</p>
      </div>

      <div className="card-placeholder">
        <h3>Padrón de Pacientes</h3>
        <p>Listado y búsqueda de pacientes registrados.</p>
      </div>
    </div>
  );
};
