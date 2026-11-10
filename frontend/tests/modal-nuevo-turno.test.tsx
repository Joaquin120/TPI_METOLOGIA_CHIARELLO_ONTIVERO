import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ModalNuevoTurno } from '../src/components/ModalNuevoTurno';
import { Profesional, Sillon, Paciente } from '../src/types';

describe('Componente ModalNuevoTurno', () => {
  const profesionales: Profesional[] = [
    { id: 1, nombre: 'Dr. Lopez', activo: true },
    { id: 2, nombre: 'Dra. Silva', activo: true },
  ];

  const sillones: Sillon[] = [
    { id: 10, nombre: 'Sillón 1', activo: true },
    { id: 20, nombre: 'Sillón 2', activo: true },
  ];

  const pacientes: Paciente[] = [
    { id: 100, tenant_id: 1, dni: '12345678', nombre: 'Juan Perez', telefono: '11223344' },
    { id: 101, tenant_id: 1, dni: '87654321', nombre: 'Maria Gomez', telefono: '55667788' },
  ];

  it('no renderiza nada si isOpen es false', () => {
    const { container } = render(
      <ModalNuevoTurno
        isOpen={false}
        fechaInicial="2026-11-10"
        profesionales={profesionales}
        sillones={sillones}
        pacientes={pacientes}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />
    );

    expect(container).toBeEmptyDOMElement();
  });

  it('valida que hora_inicio sea anterior a hora_fin antes de enviar', async () => {
    const onSubmit = vi.fn();
    render(
      <ModalNuevoTurno
        isOpen={true}
        fechaInicial="2026-11-10"
        profesionales={profesionales}
        sillones={sillones}
        pacientes={pacientes}
        onClose={vi.fn()}
        onSubmit={onSubmit}
      />
    );

    fireEvent.change(screen.getByLabelText(/paciente/i), {
      target: { value: 'Juan Perez' },
    });
    fireEvent.change(screen.getByLabelText(/profesional/i), {
      target: { value: 'Dr. Lopez' },
    });
    fireEvent.change(screen.getByLabelText(/sillón/i), {
      target: { value: 'Sillón 1' },
    });
    fireEvent.change(screen.getByLabelText(/hora inicio/i), {
      target: { value: '11:00' },
    });
    fireEvent.change(screen.getByLabelText(/hora fin/i), {
      target: { value: '10:00' },
    });

    fireEvent.click(screen.getByRole('button', { name: /agendar turno|guardar|crear/i }));

    expect(
      await screen.findByText(/la hora de inicio debe ser anterior a la hora de fin/i)
    ).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('envía los datos correctos al confirmar el formulario', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const onClose = vi.fn();

    render(
      <ModalNuevoTurno
        isOpen={true}
        fechaInicial="2026-11-10"
        profesionales={profesionales}
        sillones={sillones}
        pacientes={pacientes}
        onClose={onClose}
        onSubmit={onSubmit}
      />
    );

    fireEvent.change(screen.getByLabelText(/paciente/i), {
      target: { value: 'Juan Perez' },
    });
    fireEvent.change(screen.getByLabelText(/profesional/i), {
      target: { value: 'Dr. Lopez' },
    });
    fireEvent.change(screen.getByLabelText(/sillón/i), {
      target: { value: 'Sillón 1' },
    });
    fireEvent.change(screen.getByLabelText(/hora inicio/i), {
      target: { value: '09:00' },
    });
    fireEvent.change(screen.getByLabelText(/hora fin/i), {
      target: { value: '09:30' },
    });

    fireEvent.click(screen.getByRole('button', { name: /agendar turno|guardar|crear/i }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        paciente: 'Juan Perez',
        profesional: 'Dr. Lopez',
        sillon: 'Sillón 1',
        fecha: '2026-11-10',
        hora_inicio: '09:00',
        hora_fin: '09:30',
      });
    });
  });

  it('muestra mensaje de error de solapamiento (409) sin cerrar el modal', async () => {
    const errorSolapamiento = new Error('Solapamiento: el profesional Dr. Lopez ya tiene un turno activo');
    const onSubmit = vi.fn().mockRejectedValue(errorSolapamiento);

    render(
      <ModalNuevoTurno
        isOpen={true}
        fechaInicial="2026-11-10"
        profesionales={profesionales}
        sillones={sillones}
        pacientes={pacientes}
        onClose={vi.fn()}
        onSubmit={onSubmit}
      />
    );

    fireEvent.change(screen.getByLabelText(/paciente/i), {
      target: { value: 'Juan Perez' },
    });
    fireEvent.change(screen.getByLabelText(/profesional/i), {
      target: { value: 'Dr. Lopez' },
    });
    fireEvent.change(screen.getByLabelText(/sillón/i), {
      target: { value: 'Sillón 1' },
    });
    fireEvent.change(screen.getByLabelText(/hora inicio/i), {
      target: { value: '09:00' },
    });
    fireEvent.change(screen.getByLabelText(/hora fin/i), {
      target: { value: '09:30' },
    });

    fireEvent.click(screen.getByRole('button', { name: /agendar turno|guardar|crear/i }));

    expect(
      await screen.findByText(/Solapamiento: el profesional Dr. Lopez ya tiene un turno activo/i)
    ).toBeInTheDocument();
    // Modal remains rendered
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });
});
