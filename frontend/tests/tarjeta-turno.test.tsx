import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TarjetaTurno } from '../src/components/TarjetaTurno';
import { Turno } from '../src/types';

describe('Componente TarjetaTurno', () => {
  const turnoPendiente: Turno = {
    id: 1,
    paciente: 'Carlos Dent',
    profesional: 'Dra. Suarez',
    sillon: 'Sillón 1',
    fecha: '2026-11-10',
    hora_inicio: '09:00',
    hora_fin: '09:30',
    estado: 'PENDIENTE',
  };

  const turnoConfirmado: Turno = {
    ...turnoPendiente,
    id: 2,
    estado: 'CONFIRMADO',
  };

  const turnoCompletado: Turno = {
    ...turnoPendiente,
    id: 3,
    estado: 'COMPLETADO',
  };

  const turnoCancelado: Turno = {
    ...turnoPendiente,
    id: 4,
    estado: 'CANCELADO',
  };

  it('renderiza información básica y badge de estado PENDIENTE', () => {
    render(<TarjetaTurno turno={turnoPendiente} />);

    expect(screen.getByText('Carlos Dent')).toBeInTheDocument();
    expect(screen.getByText(/Dra\. Suarez/)).toBeInTheDocument();
    expect(screen.getByText(/Sillón 1/)).toBeInTheDocument();
    expect(screen.getByText('09:00 - 09:30')).toBeInTheDocument();

    const badge = screen.getByText('PENDIENTE');
    expect(badge).toBeInTheDocument();
  });

  it('turno PENDIENTE muestra botones Confirmar, Cancelar y Reprogramar', () => {
    const onConfirmar = vi.fn();
    const onCancelar = vi.fn();
    const onReprogramar = vi.fn();

    render(
      <TarjetaTurno
        turno={turnoPendiente}
        onConfirmar={onConfirmar}
        onCancelar={onCancelar}
        onReprogramar={onReprogramar}
      />
    );

    const btnConfirmar = screen.getByRole('button', { name: /confirmar/i });
    const btnCancelar = screen.getByRole('button', { name: /cancelar/i });
    const btnReprogramar = screen.getByRole('button', { name: /reprogramar/i });

    expect(btnConfirmar).toBeInTheDocument();
    expect(btnCancelar).toBeInTheDocument();
    expect(btnReprogramar).toBeInTheDocument();

    fireEvent.click(btnConfirmar);
    expect(onConfirmar).toHaveBeenCalledWith(turnoPendiente);

    fireEvent.click(btnCancelar);
    expect(onCancelar).toHaveBeenCalledWith(turnoPendiente);

    fireEvent.click(btnReprogramar);
    expect(onReprogramar).toHaveBeenCalledWith(turnoPendiente);
  });

  it('turno CONFIRMADO muestra botones Completar, Cancelar y Reprogramar', () => {
    const onCompletar = vi.fn();
    const onCancelar = vi.fn();

    render(
      <TarjetaTurno
        turno={turnoConfirmado}
        onCompletar={onCompletar}
        onCancelar={onCancelar}
      />
    );

    const btnCompletar = screen.getByRole('button', { name: /completar/i });
    const btnCancelar = screen.getByRole('button', { name: /cancelar/i });

    expect(btnCompletar).toBeInTheDocument();
    expect(btnCancelar).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /confirmar/i })).not.toBeInTheDocument();

    fireEvent.click(btnCompletar);
    expect(onCompletar).toHaveBeenCalledWith(turnoConfirmado);
  });

  it('turno COMPLETADO o CANCELADO no muestra botones de acción de cambio', () => {
    const { rerender } = render(<TarjetaTurno turno={turnoCompletado} />);
    expect(screen.queryByRole('button', { name: /confirmar/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /cancelar/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /completar/i })).not.toBeInTheDocument();

    rerender(<TarjetaTurno turno={turnoCancelado} />);
    expect(screen.queryByRole('button', { name: /confirmar/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /cancelar/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /completar/i })).not.toBeInTheDocument();
  });
});
