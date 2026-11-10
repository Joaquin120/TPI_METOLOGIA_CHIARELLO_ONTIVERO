import React from 'react';

export const Agenda: React.FC = () => {
  return (
    <div className="page-agenda" data-testid="page-agenda">
      <div className="page-header">
        <h1>Agenda de Turnos</h1>
        <p>Vista general y matricial de atención clínica para profesionales y sillones</p>
      </div>

      <div className="card-placeholder" data-testid="agenda-placeholder">
        <h3>Grilla Operativa de Turnos (C-12)</h3>
        <p>La matriz horaria interactiva se integrará en el siguiente change.</p>
      </div>
    </div>
  );
};
