import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  listarTurnos,
  crearTurno,
  cambiarEstadoTurno,
  confirmarTurno,
  cancelarTurno,
  completarTurno,
  reprogramarTurno,
} from '../src/api/turnos';
import { clienteApi } from '../src/api/cliente';
import { Turno, TurnoCrearPeticion, ReprogramarTurnoPeticion } from '../src/types';

describe('Cliente API Turnos (frontend/src/api/turnos.ts)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('listarTurnos genera query string adecuada con filtros múltiples', async () => {
    const mockTurnos: Turno[] = [
      {
        id: 1,
        paciente: 'Paciente 1',
        profesional: 'Dr. Perez',
        sillon: 'Sillón 1',
        fecha: '2026-11-10',
        hora_inicio: '09:00',
        hora_fin: '09:30',
        estado: 'CONFIRMADO',
      },
    ];

    const getSpy = vi.spyOn(clienteApi, 'get').mockResolvedValue(mockTurnos);

    const res = await listarTurnos({
      fecha: '2026-11-10',
      profesional_id: 2,
      sillon_id: 3,
    });

    expect(res).toEqual(mockTurnos);
    expect(getSpy).toHaveBeenCalledWith('/turnos?fecha=2026-11-10&profesional_id=2&sillon_id=3');
  });

  it('crearTurno envía petición POST con el payload correcto', async () => {
    const nuevo: TurnoCrearPeticion = {
      paciente: 'Paciente Nuevo',
      profesional: 'Dra. Gomez',
      sillon: 'Sillón 2',
      fecha: '2026-11-11',
      hora_inicio: '10:00',
      hora_fin: '10:30',
    };
    const creado: Turno = { id: 10, ...nuevo, estado: 'PENDIENTE' };

    const postSpy = vi.spyOn(clienteApi, 'post').mockResolvedValue(creado);

    const res = await crearTurno(nuevo);
    expect(res).toEqual(creado);
    expect(postSpy).toHaveBeenCalledWith('/turnos', nuevo);
  });

  it('funciones de transición llaman al endpoint con la acción correspondiente', async () => {
    const patchSpy = vi.spyOn(clienteApi, 'patch').mockResolvedValue({} as Turno);

    await cambiarEstadoTurno(1, 'confirmar');
    expect(patchSpy).toHaveBeenCalledWith('/turnos/1/estado', { accion: 'confirmar' });

    await confirmarTurno(1);
    expect(patchSpy).toHaveBeenCalledWith('/turnos/1/estado', { accion: 'confirmar' });

    await cancelarTurno(1);
    expect(patchSpy).toHaveBeenCalledWith('/turnos/1/estado', { accion: 'cancelar' });

    await completarTurno(1);
    expect(patchSpy).toHaveBeenCalledWith('/turnos/1/estado', { accion: 'completar' });
  });

  it('reprogramarTurno envía patch al endpoint de reprogramación', async () => {
    const payload: ReprogramarTurnoPeticion = {
      fecha: '2026-11-12',
      hora_inicio: '11:00',
      hora_fin: '11:45',
      profesional_id: 1,
      sillon_id: 2,
    };
    const patchSpy = vi.spyOn(clienteApi, 'patch').mockResolvedValue({} as Turno);

    await reprogramarTurno(5, payload);
    expect(patchSpy).toHaveBeenCalledWith('/turnos/5/reprogramar', payload);
  });
});

