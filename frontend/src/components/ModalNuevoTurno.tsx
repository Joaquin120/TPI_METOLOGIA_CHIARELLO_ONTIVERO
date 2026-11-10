import React, { useState, useEffect } from 'react';
import { Profesional, Sillon, Paciente, TurnoCrearPeticion } from '../types';

export interface ModalNuevoTurnoProps {
  isOpen: boolean;
  fechaInicial: string;
  profesionales: Profesional[];
  sillones: Sillon[];
  pacientes?: Paciente[];
  profesionalPreseleccionadoId?: number | null;
  onClose: () => void;
  onSubmit: (datos: TurnoCrearPeticion) => Promise<void>;
}

export const ModalNuevoTurno: React.FC<ModalNuevoTurnoProps> = ({
  isOpen,
  fechaInicial,
  profesionales,
  sillones,
  pacientes = [],
  profesionalPreseleccionadoId,
  onClose,
  onSubmit,
}) => {
  const [paciente, setPaciente] = useState('');
  const [profesional, setProfesional] = useState('');
  const [sillon, setSillon] = useState('');
  const [fecha, setFecha] = useState(fechaInicial);
  const [horaInicio, setHoraInicio] = useState('09:00');
  const [horaFin, setHoraFin] = useState('09:30');
  const [errorLocal, setErrorLocal] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setFecha(fechaInicial);
      setErrorLocal(null);
      setCargando(false);

      if (profesionalPreseleccionadoId) {
        const prof = profesionales.find((p) => p.id === profesionalPreseleccionadoId);
        if (prof) setProfesional(prof.nombre);
      } else if (profesionales.length > 0) {
        setProfesional(profesionales[0].nombre);
      }

      if (sillones.length > 0) {
        setSillon(sillones[0].nombre);
      }
    }
  }, [isOpen, fechaInicial, profesionalPreseleccionadoId, profesionales, sillones]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorLocal(null);

    if (!paciente.trim()) {
      setErrorLocal('El paciente es requerido');
      return;
    }
    if (!profesional) {
      setErrorLocal('Seleccione un profesional');
      return;
    }
    if (!sillon) {
      setErrorLocal('Seleccione un sillón');
      return;
    }
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
      await onSubmit({
        paciente: paciente.trim(),
        profesional,
        sillon,
        fecha,
        hora_inicio: horaInicio,
        hora_fin: horaFin,
      });
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error al agendar el turno';
      setErrorLocal(msg);
    } finally {
      setCargando(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-nuevo-turno-titulo"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
    >
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full overflow-hidden border border-slate-200">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h2 id="modal-nuevo-turno-titulo" className="text-lg font-semibold text-slate-800">
            Nuevo Turno
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

          <div>
            <label htmlFor="input-paciente" className="block text-sm font-medium text-slate-700 mb-1">
              Paciente
            </label>
            <input
              id="input-paciente"
              type="text"
              list="lista-pacientes"
              value={paciente}
              onChange={(e) => setPaciente(e.target.value)}
              placeholder="Nombre del paciente"
              required
              className="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {pacientes.length > 0 && (
              <datalist id="lista-pacientes">
                {pacientes.map((p) => (
                  <option key={p.id} value={p.nombre}>
                    DNI: {p.dni}
                  </option>
                ))}
              </datalist>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label
                htmlFor="select-profesional"
                className="block text-sm font-medium text-slate-700 mb-1"
              >
                Profesional
              </label>
              <select
                id="select-profesional"
                value={profesional}
                onChange={(e) => setProfesional(e.target.value)}
                required
                className="w-full border border-slate-300 rounded px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Seleccione...</option>
                {profesionales.map((p) => (
                  <option key={p.id} value={p.nombre}>
                    {p.nombre}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="select-sillon" className="block text-sm font-medium text-slate-700 mb-1">
                Sillón
              </label>
              <select
                id="select-sillon"
                value={sillon}
                onChange={(e) => setSillon(e.target.value)}
                required
                className="w-full border border-slate-300 rounded px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Seleccione...</option>
                {sillones.map((s) => (
                  <option key={s.id} value={s.nombre}>
                    {s.nombre}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="input-fecha" className="block text-sm font-medium text-slate-700 mb-1">
              Fecha
            </label>
            <input
              id="input-fecha"
              type="date"
              value={fecha}
              onChange={(e) => setFecha(e.target.value)}
              required
              className="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="input-inicio" className="block text-sm font-medium text-slate-700 mb-1">
                Hora Inicio
              </label>
              <input
                id="input-inicio"
                type="time"
                value={horaInicio}
                onChange={(e) => setHoraInicio(e.target.value)}
                required
                className="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label htmlFor="input-fin" className="block text-sm font-medium text-slate-700 mb-1">
                Hora Fin
              </label>
              <input
                id="input-fin"
                type="time"
                value={horaFin}
                onChange={(e) => setHoraFin(e.target.value)}
                required
                className="w-full border border-slate-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
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
              {cargando ? 'Guardando...' : 'Agendar Turno'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

