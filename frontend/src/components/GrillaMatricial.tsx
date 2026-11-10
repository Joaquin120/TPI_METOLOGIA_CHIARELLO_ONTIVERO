import React from 'react';
import { Turno, Profesional, Sillon, Bloqueo, EstadoTurno } from '../types';
import {
  generarFranjasHorarias,
  buscarTurnoEnSlot,
  buscarBloqueoEnSlot,
} from '../utils/matrizHoraria';

export interface RecursoColumna {
  id: number;
  nombre: string;
  tipo: 'sillon' | 'profesional';
}

export interface GrillaMatricialProps {
  fecha: string;
  turnos: Turno[];
  profesionales: Profesional[];
  sillones: Sillon[];
  bloqueos?: Bloqueo[];
  tipoAgrupacion?: 'sillon' | 'profesional';
  onCambiarAgrupacion?: (tipo: 'sillon' | 'profesional') => void;
  onTurnoClick?: (turno: Turno) => void;
  onSlotVacioClick?: (recurso: RecursoColumna, hora: string) => void;
  esRolProfesional?: boolean;
  profesionalIdActual?: number | null;
}

const ESTILOS_BADGE: Record<EstadoTurno, string> = {
  CONFIRMADO: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  PENDIENTE: 'bg-amber-100 text-amber-800 border-amber-300',
  CANCELADO: 'bg-rose-100 text-rose-800 border-rose-300',
  COMPLETADO: 'bg-slate-100 text-slate-800 border-slate-300',
};

export const GrillaMatricial: React.FC<GrillaMatricialProps> = ({
  fecha,
  turnos,
  profesionales,
  sillones,
  bloqueos = [],
  tipoAgrupacion = 'sillon',
  onCambiarAgrupacion,
  onTurnoClick,
  onSlotVacioClick,
  esRolProfesional = false,
  profesionalIdActual,
}) => {
  const franjas = generarFranjasHorarias('08:00', '20:00', 30);

  // Columnas a mostrar
  const columnas: RecursoColumna[] = React.useMemo(() => {
    if (tipoAgrupacion === 'profesional') {
      const lista =
        esRolProfesional && profesionalIdActual
          ? profesionales.filter((p) => p.id === profesionalIdActual)
          : profesionales;
      return lista.map((p) => ({ id: p.id, nombre: p.nombre, tipo: 'profesional' }));
    }
    return sillones.map((s) => ({ id: s.id, nombre: s.nombre, tipo: 'sillon' }));
  }, [tipoAgrupacion, profesionales, sillones, esRolProfesional, profesionalIdActual]);

  return (
    <div className="bg-white rounded-lg shadow-sm border border-slate-200 overflow-hidden">
      <div className="p-4 border-b border-slate-100 flex flex-wrap items-center justify-between gap-3 bg-slate-50">
        <div className="text-sm font-semibold text-slate-700">
          Vista Matricial de Atención — <span className="text-blue-600">{fecha}</span>
        </div>

        {!esRolProfesional && onCambiarAgrupacion && (
          <div className="inline-flex rounded-md shadow-sm border border-slate-200 bg-white p-0.5">
            <button
              type="button"
              onClick={() => onCambiarAgrupacion('sillon')}
              className={`px-3 py-1 text-xs font-medium rounded ${
                tipoAgrupacion === 'sillon'
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Por Sillones
            </button>
            <button
              type="button"
              onClick={() => onCambiarAgrupacion('profesional')}
              className={`px-3 py-1 text-xs font-medium rounded ${
                tipoAgrupacion === 'profesional'
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Por Profesionales
            </button>
          </div>
        )}
      </div>

      <div className="overflow-x-auto max-h-[700px] overflow-y-auto">
        <table className="min-w-full divide-y divide-slate-200 border-collapse table-fixed text-left">
          <thead className="bg-slate-100 sticky top-0 z-20 shadow-sm">
            <tr>
              <th className="w-24 px-3 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider sticky left-0 bg-slate-100 z-30 border-r border-slate-200">
                Horario
              </th>
              {columnas.map((col) => (
                <th
                  key={`${col.tipo}-${col.id}`}
                  className="px-3 py-2 text-xs font-semibold text-slate-700 uppercase tracking-wider border-r border-slate-200 min-w-[180px]"
                >
                  {col.nombre}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-slate-100">
            {franjas.map((hora) => (
              <tr key={hora} className="hover:bg-slate-50/50 transition-colors">
                <td className="px-3 py-2 text-xs font-mono font-medium text-slate-500 bg-slate-50 sticky left-0 z-10 border-r border-slate-200">
                  {hora}
                </td>
                {columnas.map((col) => {
                  const bloqueo =
                    col.tipo === 'sillon'
                      ? buscarBloqueoEnSlot(bloqueos, col.id, fecha, hora, 30)
                      : undefined;

                  const turno = buscarTurnoEnSlot(turnos, col.nombre, col.tipo, hora, 30);

                  if (bloqueo) {
                    return (
                      <td
                        key={`${col.tipo}-${col.id}-${hora}`}
                        className="p-1 border-r border-slate-200 bg-amber-50/80 border-dashed"
                      >
                        <div className="p-1.5 rounded text-xs bg-amber-100 text-amber-900 border border-amber-300 font-medium">
                          ⚠️ Mantenimiento: {bloqueo.motivo}
                        </div>
                      </td>
                    );
                  }

                  if (turno) {
                    const estiloBadge = ESTILOS_BADGE[turno.estado] || ESTILOS_BADGE.PENDIENTE;
                    return (
                      <td
                        key={`${col.tipo}-${col.id}-${hora}`}
                        className="p-1 border-r border-slate-200"
                      >
                        <div
                          onClick={() => onTurnoClick && onTurnoClick(turno)}
                          className={`p-1.5 rounded text-xs border shadow-xs cursor-pointer hover:opacity-90 transition-opacity ${estiloBadge}`}
                        >
                          <div className="font-semibold truncate">{turno.paciente}</div>
                          <div className="text-[10px] text-slate-600 truncate">
                            {col.tipo === 'sillon' ? turno.profesional : turno.sillon} ({turno.hora_inicio}-{turno.hora_fin})
                          </div>
                        </div>
                      </td>
                    );
                  }

                  return (
                    <td
                      key={`${col.tipo}-${col.id}-${hora}`}
                      data-testid={`slot-${col.nombre}-${hora}`}
                      onClick={() => onSlotVacioClick && onSlotVacioClick(col, hora)}
                      className="p-1 border-r border-slate-200 hover:bg-blue-50/50 cursor-pointer transition-colors"
                    >
                      <div className="h-7 w-full flex items-center justify-center text-transparent hover:text-blue-500 text-xs font-bold">
                        +
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

