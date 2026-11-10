import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { Turno, Profesional, Sillon, Paciente, TurnoCrearPeticion, ReprogramarTurnoPeticion } from '../types';
import {
  listarTurnos,
  crearTurno,
  confirmarTurno,
  cancelarTurno,
  completarTurno,
  reprogramarTurno,
} from '../api/turnos';
import { listarProfesionales, listarSillones } from '../api/recursos';
import { listarPacientes } from '../api/pacientes';
import { FiltrosAgenda, FiltrosAgendaValores } from '../components/FiltrosAgenda';
import { TarjetaTurno } from '../components/TarjetaTurno';
import { ModalNuevoTurno } from '../components/ModalNuevoTurno';
import { ModalReprogramarTurno } from '../components/ModalReprogramarTurno';

export const Agenda: React.FC = () => {
  const { usuario } = useAuth();
  const esRolProfesional = usuario?.rol === 'Profesional';

  const [fecha, setFecha] = useState<string>(() => new Date().toISOString().split('T')[0]);
  const [profesionalId, setProfesionalId] = useState<number | null>(
    esRolProfesional ? usuario?.profesional_id ?? null : null
  );
  const [sillonId, setSillonId] = useState<number | null>(null);

  const [turnos, setTurnos] = useState<Turno[]>([]);
  const [profesionales, setProfesionales] = useState<Profesional[]>([]);
  const [sillones, setSillones] = useState<Sillon[]>([]);
  const [pacientes, setPacientes] = useState<Paciente[]>([]);

  const [cargando, setCargando] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [modalNuevoAbierto, setModalNuevoAbierto] = useState<boolean>(false);
  const [turnoAReprogramar, setTurnoAReprogramar] = useState<Turno | null>(null);

  useEffect(() => {
    if (esRolProfesional && usuario?.profesional_id) {
      setProfesionalId(usuario.profesional_id);
    }
  }, [esRolProfesional, usuario]);

  // Cargar recursos auxiliares una sola vez
  useEffect(() => {
    let montado = true;
    const cargarRecursos = async () => {
      try {
        const [profs, sills, pacs] = await Promise.all([
          listarProfesionales().catch(() => []),
          listarSillones().catch(() => []),
          listarPacientes().catch(() => []),
        ]);
        if (montado) {
          setProfesionales(profs);
          setSillones(sills);
          setPacientes(pacs);
        }
      } catch (err: unknown) {
        console.error('Error al cargar recursos para agenda:', err);
      }
    };
    cargarRecursos();
    return () => {
      montado = false;
    };
  }, []);

  const cargarTurnos = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const data = await listarTurnos({
        fecha,
        profesional_id: profesionalId ?? undefined,
        sillon_id: sillonId ?? undefined,
      });
      // Orden cronológico por hora_inicio
      const ordenados = [...data].sort((a, b) => a.hora_inicio.localeCompare(b.hora_inicio));
      setTurnos(ordenados);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error al consultar turnos';
      setError(msg);
    } finally {
      setCargando(false);
    }
  }, [fecha, profesionalId, sillonId]);

  useEffect(() => {
    cargarTurnos();
  }, [cargarTurnos]);

  const handleFiltrosChange = (nuevos: FiltrosAgendaValores) => {
    setFecha(nuevos.fecha);
    if (!esRolProfesional) {
      setProfesionalId(nuevos.profesional_id ?? null);
    }
    setSillonId(nuevos.sillon_id ?? null);
  };

  const handleConfirmar = async (turno: Turno) => {
    if (turno.id === null) return;
    try {
      await confirmarTurno(turno.id);
      await cargarTurnos();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'No se pudo confirmar el turno';
      setError(msg);
    }
  };

  const handleCancelar = async (turno: Turno) => {
    if (turno.id === null) return;
    try {
      await cancelarTurno(turno.id);
      await cargarTurnos();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'No se pudo cancelar el turno';
      setError(msg);
    }
  };

  const handleCompletar = async (turno: Turno) => {
    if (turno.id === null) return;
    try {
      await completarTurno(turno.id);
      await cargarTurnos();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'No se pudo completar el turno';
      setError(msg);
    }
  };

  const handleCrearTurno = async (datos: TurnoCrearPeticion) => {
    await crearTurno(datos);
    await cargarTurnos();
  };

  const handleReprogramarTurno = async (turnoId: number, datos: ReprogramarTurnoPeticion) => {
    await reprogramarTurno(turnoId, datos);
    await cargarTurnos();
  };

  return (
    <div className="page-agenda p-6 max-w-7xl mx-auto" data-testid="page-agenda">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Agenda de Turnos</h1>
          <p className="text-sm text-slate-600">
            Vista operativa y matricial de atención clínica para profesionales y sillones
          </p>
        </div>

        {!esRolProfesional && (
          <button
            type="button"
            onClick={() => setModalNuevoAbierto(true)}
            className="inline-flex items-center justify-center bg-blue-600 hover:bg-blue-700 text-white font-medium px-4 py-2 rounded-lg shadow-sm transition-colors"
          >
            + Nuevo Turno
          </button>
        )}
      </div>

      <FiltrosAgenda
        fecha={fecha}
        profesionalId={profesionalId}
        sillonId={sillonId}
        profesionales={profesionales}
        sillones={sillones}
        esRolProfesional={esRolProfesional}
        onFiltrosChange={handleFiltrosChange}
      />

      {error && (
        <div
          role="alert"
          className="mb-4 p-4 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-sm flex justify-between items-center"
        >
          <span>{error}</span>
          <button
            type="button"
            onClick={() => setError(null)}
            className="text-rose-500 hover:text-rose-700 font-bold ml-2"
          >
            &times;
          </button>
        </div>
      )}

      {cargando ? (
        <div className="py-12 text-center text-slate-500 font-medium">Cargando turnos...</div>
      ) : turnos.length === 0 ? (
        <div className="bg-white rounded-lg p-8 border border-slate-200 text-center text-slate-500 shadow-sm">
          <p className="text-base font-medium">No hay turnos registrados para los filtros seleccionados.</p>
          <p className="text-sm text-slate-400 mt-1">Pruebe seleccionando otra fecha o profesional.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {turnos.map((turno) => (
            <TarjetaTurno
              key={turno.id ?? `${turno.paciente}-${turno.hora_inicio}`}
              turno={turno}
              onConfirmar={handleConfirmar}
              onCancelar={handleCancelar}
              onCompletar={handleCompletar}
              onReprogramar={(t) => setTurnoAReprogramar(t)}
            />
          ))}
        </div>
      )}

      <ModalNuevoTurno
        isOpen={modalNuevoAbierto}
        fechaInicial={fecha}
        profesionales={profesionales}
        sillones={sillones}
        pacientes={pacientes}
        profesionalPreseleccionadoId={esRolProfesional ? profesionalId : undefined}
        onClose={() => setModalNuevoAbierto(false)}
        onSubmit={handleCrearTurno}
      />

      <ModalReprogramarTurno
        isOpen={turnoAReprogramar !== null}
        turno={turnoAReprogramar}
        onClose={() => setTurnoAReprogramar(null)}
        onSubmit={handleReprogramarTurno}
      />
    </div>
  );
};
