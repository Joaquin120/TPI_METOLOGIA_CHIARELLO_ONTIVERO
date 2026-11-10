import React from 'react';
import { Profesional, Sillon } from '../types';

export interface FiltrosAgendaValores {
  fecha: string;
  profesional_id?: number | null;
  sillon_id?: number | null;
}

export interface FiltrosAgendaProps {
  fecha: string;
  profesionalId?: number | null;
  sillonId?: number | null;
  profesionales: Profesional[];
  sillones: Sillon[];
  esRolProfesional?: boolean;
  onFiltrosChange: (nuevosFiltros: FiltrosAgendaValores) => void;
}

export const FiltrosAgenda: React.FC<FiltrosAgendaProps> = ({
  fecha,
  profesionalId,
  sillonId,
  profesionales,
  sillones,
  esRolProfesional = false,
  onFiltrosChange,
}) => {
  const handleFechaChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFiltrosChange({
      fecha: e.target.value,
      profesional_id: profesionalId,
      sillon_id: sillonId,
    });
  };

  const handleHoy = () => {
    const hoy = new Date().toISOString().split('T')[0];
    onFiltrosChange({
      fecha: hoy,
      profesional_id: profesionalId,
      sillon_id: sillonId,
    });
  };

  const handleProfesionalChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    onFiltrosChange({
      fecha,
      profesional_id: val ? Number(val) : null,
      sillon_id: sillonId,
    });
  };

  const handleSillonChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    onFiltrosChange({
      fecha,
      profesional_id: profesionalId,
      sillon_id: val ? Number(val) : null,
    });
  };

  return (
    <div className="bg-white p-4 rounded-lg shadow-sm border border-slate-200 mb-6 flex flex-wrap gap-4 items-end">
      <div className="flex flex-col">
        <label htmlFor="filtro-fecha" className="text-sm font-medium text-slate-700 mb-1">
          Fecha
        </label>
        <div className="flex gap-2">
          <input
            id="filtro-fecha"
            type="date"
            value={fecha}
            onChange={handleFechaChange}
            className="border border-slate-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="button"
            onClick={handleHoy}
            className="bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded text-sm font-medium transition-colors"
          >
            Hoy
          </button>
        </div>
      </div>

      <div className="flex flex-col min-w-[200px]">
        <label htmlFor="filtro-profesional" className="text-sm font-medium text-slate-700 mb-1">
          Profesional
        </label>
        <select
          id="filtro-profesional"
          value={profesionalId ?? ''}
          onChange={handleProfesionalChange}
          disabled={esRolProfesional}
          className={`border border-slate-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
            esRolProfesional ? 'bg-slate-100 text-slate-500 cursor-not-allowed' : 'bg-white'
          }`}
        >
          {!esRolProfesional && <option value="">Todos los profesionales</option>}
          {profesionales.map((p) => (
            <option key={p.id} value={p.id}>
              {p.nombre} {p.especialidad ? `(${p.especialidad})` : ''}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col min-w-[180px]">
        <label htmlFor="filtro-sillon" className="text-sm font-medium text-slate-700 mb-1">
          Sillón
        </label>
        <select
          id="filtro-sillon"
          value={sillonId ?? ''}
          onChange={handleSillonChange}
          className="border border-slate-300 rounded px-3 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Todos los sillones</option>
          {sillones.map((s) => (
            <option key={s.id} value={s.id}>
              {s.nombre}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
};

