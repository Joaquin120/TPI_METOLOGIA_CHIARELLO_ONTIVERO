import React, { useState, useEffect } from 'react';
import { Turno, ReprogramarTurnoPeticion } from '../types';

export interface ModalReprogramarTurnoProps {
  isOpen: boolean;
  turno: Turno | null;
  onClose: () => void;
  onSubmit: (turnoId: number, datos: ReprogramarTurnoPeticion) => Promise<void>;
}

export const ModalReprogramarTurno: React.FC<ModalReprogramarTurnoProps> = ({
  isOpen,
  turno,
  onClose,
  onSubmit,
}) => {
  const [fecha, setFecha] = useState('');
  const [horaInicio, setHoraInicio] = useState('');
  const [horaFin, setHoraFin] = useState('');
  const [motivo, setMotivo] = useState('');
  const [errorLocal, setErrorLocal] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);

  useEffect(() => {
    if (isOpen && turno) {
      setFecha(turno.fecha);
      setHoraInicio(turno.hora_inicio);
      setHoraFin(turno.hora_fin);
      setMotivo('');
      setErrorLocal(null);
      setCargando(false);
    }
  }, [isOpen, turno]);

  if (!isOpen || !turno || turno.id === null) return null;
  const turnoId = turno.id;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorLocal(null);

    if (!fecha) {
      setErrorLocal('La fecha es requerida');
      return;
    }
    if (horaInicio >= horaFin) {
      setErrorLocal('La hora de inicio debe ser anterior a la hora de fin');
      return;
    }

    try {
      setCargando(true);
      await onSubmit(turnoId, {
        fecha,
        hora_inicio: horaInicio,
        hora_fin: horaFin,
        motivo: motivo.trim() || null,
      });
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error al reprogramar el turno';
      setErrorLocal(msg);
    } finally {
      setCargando(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-reprogramar-titulo"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
    >
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full overflow-hidden border border-slate-200">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h2 id="modal-reprogramar-titulo" className="text-lg font-semibold text-slate-800">
            Reprogramar Turno
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 text-xl font-bold leading-none"
            aria-label="Cerrar"
          >
            &times;
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {errorLocal && (
            <div
              role="alert"
              className="p-3 text-sm rounded bg-rose-50 text-rose-800 border border-rose-300"
            >
              {errorLocal}
            </div>
          )}

          <div className="bg-slate-50 p-3 rounded text-sm text-slate-700 space-y-1">
            <p>
              <span className="font-medium text-slate-500">Paciente:</span> {turno.paciente}
            </p>
            <p>
              <span className="font-medium text-slate-500">Profesional:</span> {turno.profesional}
            </p>
            <p>
              <span className="font-medium text-slate-500">Sillón:</span> {turno.sillon}
            </p>
            <p>
              <span className="font-medium text-slate-500">Horario actual:</span> {turno.fecha} ({turno.hora_inicio} - {turno.hora_fin})
            </p>
          </div>

          <div>
            <label htmlFor="input-nueva-fecha" className="block text-sm font-medium text-slate-700 mb-1">
              Nueva Fecha
            </label>
            <input
              id="input-nueva-fecha"
              type="date"
              value={fecha}
              onChange={(e) => setFecha(e.target.value)}
              required
              className="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="input-reprog-inicio" className="block text-sm font-medium text-slate-700 mb-1">
                Hora Inicio
              </label>
              <input
                id="input-reprog-inicio"
                type="time"
                value={horaInicio}
                onChange={(e) => setHoraInicio(e.target.value)}
                required
                className="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label htmlFor="input-reprog-fin" className="block text-sm font-medium text-slate-700 mb-1">
                Hora Fin
              </label>
              <input
                id="input-reprog-fin"
                type="time"
                value={horaFin}
                onChange={(e) => setHoraFin(e.target.value)}
                required
                className="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div>
            <label htmlFor="input-motivo" className="block text-sm font-medium text-slate-700 mb-1">
              Motivo (opcional)
            </label>
            <input
              id="input-motivo"
              type="text"
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              placeholder="Ej: Solicitud del paciente"
              className="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              disabled={cargando}
              className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-800 bg-slate-100 hover:bg-slate-200 rounded transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={cargando}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded transition-colors disabled:opacity-50"
            >
              {cargando ? 'Reprogramando...' : 'Reprogramar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
