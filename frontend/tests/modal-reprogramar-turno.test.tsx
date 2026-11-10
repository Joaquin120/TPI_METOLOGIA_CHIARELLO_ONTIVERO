import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ModalReprogramarTurno } from '../src/components/ModalReprogramarTurno';
import { Turno } from '../src/types';

describe('Componente ModalReprogramarTurno', () => {
  const turnoMock: Turno = {
    id: 55,
    paciente: 'Carlos Dent',
    profesional: 'Dr. Lopez',
    sillon: 'Sillón 1',
    fecha: '2026-11-10',
    hora_inicio: '10:00',
    hora_fin: '10:30',
    estado: 'CONFIRMADO',
  };

  it('no renderiza nada si isOpen es false o turno es null', () => {
    const { container, rerender } = render(
      <ModalReprogramarTurno
        isOpen={false}
        turno={turnoMock}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />
    );
    expect(container).toBeEmptyDOMElement();

    rerender(
      <ModalReprogramarTurno
        isOpen={true}
        turno={null}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('valida que hora_inicio sea anterior a hora_fin', async () => {
    const onSubmit = vi.fn();
    render(
      <ModalReprogramarTurno
        isOpen={true}
        turno={turnoMock}
        onClose={vi.fn()}
        onSubmit={onSubmit}
      />
    );

    fireEvent.change(screen.getByLabelText(/hora inicio/i), {
      target: { value: '15:00' },
    });
    fireEvent.change(screen.getByLabelText(/hora fin/i), {
      target: { value: '14:00' },
    });

    fireEvent.click(screen.getByRole('button', { name: /reprogramar|guardar|confirmar/i }));

    expect(
      await screen.findByText(/la hora de inicio debe ser anterior a la hora de fin/i)
    ).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('envía los datos actualizados al confirmar reprogramación', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const onClose = vi.fn();

    render(
      <ModalReprogramarTurno
        isOpen={true}
        turno={turnoMock}
        onClose={onClose}
        onSubmit={onSubmit}
      />
    );

    fireEvent.change(screen.getByLabelText(/nueva fecha/i), {
      target: { value: '2026-11-12' },
    });
    fireEvent.change(screen.getByLabelText(/hora inicio/i), {
      target: { value: '11:00' },
    });
    fireEvent.change(screen.getByLabelText(/hora fin/i), {
      target: { value: '11:45' },
    });

    fireEvent.click(screen.getByRole('button', { name: /reprogramar/i }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(55, {
        fecha: '2026-11-12',
        hora_inicio: '11:00',
        hora_fin: '11:45',
        motivo: null,
      });
    });
  });

  it('muestra mensaje de conflicto de solapamiento sin cerrar modal', async () => {
    const errorConflicto = new Error('Solapamiento en nuevo horario');
    const onSubmit = vi.fn().mockRejectedValue(errorConflicto);

    render(
      <ModalReprogramarTurno
        isOpen={true}
        turno={turnoMock}
        onClose={vi.fn()}
        onSubmit={onSubmit}
      />
    );

    fireEvent.change(screen.getByLabelText(/hora inicio/i), {
      target: { value: '11:00' },
    });
    fireEvent.change(screen.getByLabelText(/hora fin/i), {
      target: { value: '11:30' },
    });

    fireEvent.click(screen.getByRole('button', { name: /reprogramar/i }));

    expect(await screen.findByText(/Solapamiento en nuevo horario/i)).toBeInTheDocument();
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });
});
