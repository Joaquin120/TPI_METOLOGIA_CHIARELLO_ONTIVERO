import { describe, it, expect } from 'vitest';
import {
  generarFranjasHorarias,
  horaAMinutos,
  minutosAHora,
  turnoIntersecaFranja,
  buscarTurnoEnSlot,
} from '../src/utils/matrizHoraria';
import { Turno } from '../src/types';

describe('Utilidades de Matriz Horaria (frontend/src/utils/matrizHoraria.ts)', () => {
  it('horaAMinutos y minutosAHora convierten correctamente', () => {
    expect(horaAMinutos('08:00')).toBe(480);
    expect(horaAMinutos('14:30')).toBe(870);
    expect(minutosAHora(480)).toBe('08:00');
    expect(minutosAHora(870)).toBe('14:30');
  });

  it('generarFranjasHorarias genera secuencia correcta de franjas de 30 minutos', () => {
    const franjas = generarFranjasHorarias('08:00', '10:00', 30);
    expect(franjas).toEqual(['08:00', '08:30', '09:00', '09:30']);
  });

  it('turnoIntersecaFranja detecta colisiones de intervalos semiabiertos', () => {
    // Franja de prueba: 09:00 a 09:30
    // Turno: 09:00 a 09:30 -> Sí interseca
    expect(turnoIntersecaFranja('09:00', '09:30', '09:00', 30)).toBe(true);

    // Turno contiguo anterior: 08:30 a 09:00 -> NO interseca (intervalo semiabierto)
    expect(turnoIntersecaFranja('08:30', '09:00', '09:00', 30)).toBe(false);

    // Turno contiguo posterior: 09:30 a 10:00 -> NO interseca
    expect(turnoIntersecaFranja('09:30', '10:00', '09:00', 30)).toBe(false);

    // Turno largo: 08:30 a 10:30 -> Sí interseca
    expect(turnoIntersecaFranja('08:30', '10:30', '09:00', 30)).toBe(true);
  });

  it('buscarTurnoEnSlot encuentra el turno correspondiente al recurso y slot', () => {
    const turnos: Turno[] = [
      {
        id: 1,
        paciente: 'Carlos Dent',
        profesional: 'Dr. Lopez',
        sillon: 'Sillón 1',
        fecha: '2026-11-10',
        hora_inicio: '09:00',
        hora_fin: '10:00',
        estado: 'CONFIRMADO',
      },
    ];

    // Busca por sillón en slot 09:30
    const encontradoSillon = buscarTurnoEnSlot(turnos, 'Sillón 1', 'sillon', '09:30', 30);
    expect(encontradoSillon?.id).toBe(1);

    // Busca por otro sillón en slot 09:30 -> No debe encontrar
    const noEncontradoSillon = buscarTurnoEnSlot(turnos, 'Sillón 2', 'sillon', '09:30', 30);
    expect(noEncontradoSillon).toBeUndefined();

    // Busca por profesional en slot 09:00
    const encontradoProf = buscarTurnoEnSlot(turnos, 'Dr. Lopez', 'profesional', '09:00', 30);
    expect(encontradoProf?.id).toBe(1);
  });
});

