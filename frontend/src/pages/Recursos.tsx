import React from 'react';

export const Recursos: React.FC = () => {
  return (
    <div className="page-recursos" data-testid="page-recursos">
      <div className="page-header">
        <h1>Gestión de Recursos Clínicos</h1>
        <p>Administración de profesionales, sillones de atención y bloqueos técnicos</p>
      </div>

      <div className="card-placeholder">
        <h3>Profesionales y Sillones</h3>
        <p>Gestión de disponibilidad y mantenimiento preventivo.</p>
      </div>
    </div>
  );
};
