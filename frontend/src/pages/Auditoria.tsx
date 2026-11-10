import React from 'react';

export const Auditoria: React.FC = () => {
  return (
    <div className="page-auditoria" data-testid="page-auditoria">
      <div className="page-header">
        <h1>Bitácora de Auditoría</h1>
        <p>Registro inmutable de acciones y trazabilidad histórica de eventos</p>
      </div>

      <div className="card-placeholder">
        <h3>Eventos de Auditoría</h3>
        <p>Consulta exclusiva para administradores de clínica.</p>
      </div>
    </div>
  );
};
