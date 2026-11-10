import React from 'react';
import { Turno, EstadoTurno } from '../types';

export interface TarjetaTurnoProps {
  turno: Turno;
  onConfirmar?: (turno: Turno) => void;
  onCancelar?: (turno: Turno) => void;
  onCompletar?: (turno: Turno) => void;
  onReprogramar?: (turno: Turno) => void;
  deshabilitarAcciones?: boolean;
}

const ESTILOS_ESTADO: Record<EstadoTurno, { badge: string; borde: string }> = {
  CONFIRMADO: {
    badge: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    borde: 'border-l-4 border-l-emerald-500',
  },
  PENDIENTE: {
    badge: 'bg-amber-100 text-amber-800 border-amber-300',
    borde: 'border-l-4 border-l-amber-500',
  },
  CANCELADO: {
    badge: 'bg-rose-100 text-rose-800 border-rose-300',
    borde: 'border-l-4 border-l-rose-500',
  },
  COMPLETADO: {
    badge: 'bg-slate-100 text-slate-800 border-slate-300',
    borde: 'border-l-4 border-l-slate-400',
  },
};

export const TarjetaTurno: React.FC<TarjetaTurnoProps> = ({
  turno,
  onConfirmar,
  onCancelar,
  onCompletar,
  onReprogramar,
  deshabilitarAcciones = false,
}) => {
  const estilo = ESTILOS_ESTADO[turno.estado] || ESTILOS_ESTADO.PENDIENTE;
  const esTerminal = turno.estado === 'CANCELADO' || turno.estado === 'COMPLETADO';

  return (
    <div
      className={`bg-white rounded-lg p-4 shadow-sm border border-slate-200 ${estilo.borde} flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all hover:shadow-md`}
    >
      <div className="flex-1">
        <div className="flex items-center gap-3 mb-1">
          <span className="text-lg font-semibold text-slate-900">{turno.paciente}</span>
          <span
            className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border ${estilo.badge}`}
          >
            {turno.estado}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-sm text-slate-600 mt-2">
          <div>
            <span className="font-medium text-slate-500">Horario: </span>
            <span className="font-semibold text-slate-800">
              {turno.hora_inicio} - {turno.hora_fin}
            </span>
          </div>
          <div>
            <span className="font-medium text-slate-500">Profesional: </span>
            <span className="text-slate-800">{turno.profesional}</span>
          </div>
          <div>
            <span className="font-medium text-slate-500">Sillón: </span>
            <span className="text-slate-800">{turno.sillon}</span>
          </div>
        </div>
      </div>

      {!esTerminal && !deshabilitarAcciones && (
        <div className="flex flex-wrap items-center gap-2 pt-2 md:pt-0 border-t md:border-t-0 border-slate-100">
          {turno.estado === 'PENDIENTE' && onConfirmar && (
            <button
              type="button"
              onClick={() => onConfirmar(turno)}
              className="bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded text-sm font-medium transition-colors"
            >
              Confirmar
            </button>
          )}

          {turno.estado === 'CONFIRMADO' && onCompletar && (
            <button
              type="button"
              onClick={() => onCompletar(turno)}
              className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded text-sm font-medium transition-colors"
            >
              Completar
            </button>
          )}

          {onReprogramar && (
            <button
              type="button"
              onClick={() => onReprogramar(turno)}
              className="bg-amber-100 hover:bg-amber-200 text-amber-800 px-3 py-1.5 rounded text-sm font-medium transition-colors border border-amber-300"
            >
              Reprogramar
            </button>
          )}

          {onCancelar && (
            <button
              type="button"
              onClick={() => onCancelar(turno)}
              className="bg-rose-50 hover:bg-rose-100 text-rose-700 px-3 py-1.5 rounded text-sm font-medium transition-colors border border-rose-200"
            >
              Cancelar
            </button>
          )}
        </div>
      )}
    </div>
  );
};

