import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { GrillaMatricial } from '../src/components/GrillaMatricial';
import { Turno, Profesional, Sillon, Bloqueo } from '../src/types';

describe('Componente GrillaMatricial', () => {
  const profesionales: Profesional[] = [
    { id: 1, nombre: 'Dr. Lopez', activo: true },
    { id: 2, nombre: 'Dra. Silva', activo: true },
  ];

  const sillones: Sillon[] = [
    { id: 10, nombre: 'Sillón 1', activo: true },
    { id: 20, nombre: 'Sillón 2', activo: true },
  ];

  const turnos: Turno[] = [
    {
      id: 100,
      paciente: 'Carlos Dent',
      profesional: 'Dr. Lopez',
      sillon: 'Sillón 1',
      fecha: '2026-11-10',
      hora_inicio: '09:00',
      hora_fin: '09:30',
      estado: 'CONFIRMADO',
    },
    {
      id: 101,
      paciente: 'Maria Perez',
      profesional: 'Dra. Silva',
      sillon: 'Sillón 2',
      fecha: '2026-11-10',
      hora_inicio: '10:00',
      hora_fin: '10:30',
      estado: 'PENDIENTE',
    },
  ];

  it('renderiza cabeceras de columnas por sillón y franjas horarias', () => {
    render(
      <GrillaMatricial
        fecha="2026-11-10"
        turnos={turnos}
        profesionales={profesionales}
        sillones={sillones}
        tipoAgrupacion="sillon"
      />
    );

    expect(screen.getByText('Sillón 1')).toBeInTheDocument();
    expect(screen.getByText('Sillón 2')).toBeInTheDocument();
    expect(screen.getByText('08:00')).toBeInTheDocument();
    expect(screen.getByText('09:00')).toBeInTheDocument();

    // Turno visible
    expect(screen.getByText('Carlos Dent')).toBeInTheDocument();
  });

  it('permite alternar agrupación a profesionales y renderiza sus columnas', () => {
    const onCambiarAgrupacion = vi.fn();
    render(
      <GrillaMatricial
        fecha="2026-11-10"
        turnos={turnos}
        profesionales={profesionales}
        sillones={sillones}
        tipoAgrupacion="sillon"
        onCambiarAgrupacion={onCambiarAgrupacion}
      />
    );

    const btnProfs = screen.getByRole('button', { name: /profesionales/i });
    fireEvent.click(btnProfs);
    expect(onCambiarAgrupacion).toHaveBeenCalledWith('profesional');
  });

  it('dispara onTurnoClick al hacer clic sobre un turno', () => {
    const onTurnoClick = vi.fn();
    render(
      <GrillaMatricial
        fecha="2026-11-10"
        turnos={turnos}
        profesionales={profesionales}
        sillones={sillones}
        tipoAgrupacion="sillon"
        onTurnoClick={onTurnoClick}
      />
    );

    const turnoElemento = screen.getByText('Carlos Dent');
    fireEvent.click(turnoElemento);

    expect(onTurnoClick).toHaveBeenCalledWith(turnos[0]);
  });

  it('dispara onSlotVacioClick al hacer clic sobre una celda libre', () => {
    const onSlotVacioClick = vi.fn();
    render(
      <GrillaMatricial
        fecha="2026-11-10"
        turnos={turnos}
        profesionales={profesionales}
        sillones={sillones}
        tipoAgrupacion="sillon"
        onSlotVacioClick={onSlotVacioClick}
      />
    );

    // Slot libre en Sillón 1 a las 08:00
    const slotVacio = screen.getByTestId('slot-Sillón 1-08:00');
    fireEvent.click(slotVacio);

    expect(onSlotVacioClick).toHaveBeenCalledWith(
      expect.objectContaining({ nombre: 'Sillón 1', tipo: 'sillon' }),
      '08:00'
    );
  });

  it('muestra celdas de bloqueo por mantenimiento en la agrupación por sillón', () => {
    const bloqueos: Bloqueo[] = [
      {
        id: 5,
        tenant_id: 1,
        sillon_id: 10,
        fecha_hora_inicio: '2026-11-10T08:00:00',
        fecha_hora_fin: '2026-11-10T09:00:00',
        motivo: 'Service técnico',
      },
    ];

    render(
      <GrillaMatricial
        fecha="2026-11-10"
        turnos={turnos}
        profesionales={profesionales}
        sillones={sillones}
        bloqueos={bloqueos}
        tipoAgrupacion="sillon"
      />
    );

    expect(screen.getAllByText(/Service técnico/i)[0]).toBeInTheDocument();
  });
});

