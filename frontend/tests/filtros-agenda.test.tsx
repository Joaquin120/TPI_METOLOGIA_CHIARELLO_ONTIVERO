import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { FiltrosAgenda } from '../src/components/FiltrosAgenda';
import { Profesional, Sillon } from '../src/types';

describe('Componente FiltrosAgenda', () => {
  const profesionales: Profesional[] = [
    { id: 10, nombre: 'Dr. Lopez', activo: true },
    { id: 20, nombre: 'Dra. Silva', activo: true },
  ];

  const sillones: Sillon[] = [
    { id: 1, nombre: 'Sillón Azul', activo: true },
    { id: 2, nombre: 'Sillón Verde', activo: true },
  ];

  it('renderiza inputs de fecha, profesional y sillón con valores iniciales', () => {
    const onFiltrosChange = vi.fn();
    render(
      <FiltrosAgenda
        fecha="2026-11-10"
        profesionalId={null}
        sillonId={null}
        profesionales={profesionales}
        sillones={sillones}
        esRolProfesional={false}
        onFiltrosChange={onFiltrosChange}
      />
    );

    const inputFecha = screen.getByLabelText(/fecha/i) as HTMLInputElement;
    expect(inputFecha.value).toBe('2026-11-10');

    const selectProfesional = screen.getByLabelText(/profesional/i) as HTMLSelectElement;
    expect(selectProfesional.disabled).toBe(false);

    const selectSillon = screen.getByLabelText(/sillón/i) as HTMLSelectElement;
    expect(selectSillon.value).toBe('');
  });

  it('dispara onFiltrosChange cuando el usuario cambia la fecha o recursos', () => {
    const onFiltrosChange = vi.fn();
    render(
      <FiltrosAgenda
        fecha="2026-11-10"
        profesionalId={null}
        sillonId={null}
        profesionales={profesionales}
        sillones={sillones}
        esRolProfesional={false}
        onFiltrosChange={onFiltrosChange}
      />
    );

    fireEvent.change(screen.getByLabelText(/fecha/i), {
      target: { value: '2026-11-15' },
    });
    expect(onFiltrosChange).toHaveBeenCalledWith(
      expect.objectContaining({ fecha: '2026-11-15' })
    );

    fireEvent.change(screen.getByLabelText(/profesional/i), {
      target: { value: '20' },
    });
    expect(onFiltrosChange).toHaveBeenCalledWith(
      expect.objectContaining({ profesional_id: 20 })
    );
  });

  it('bloquea el selector de profesional si el usuario tiene rol Profesional', () => {
    const onFiltrosChange = vi.fn();
    render(
      <FiltrosAgenda
        fecha="2026-11-10"
        profesionalId={10}
        sillonId={null}
        profesionales={profesionales}
        sillones={sillones}
        esRolProfesional={true}
        onFiltrosChange={onFiltrosChange}
      />
    );

    const selectProfesional = screen.getByLabelText(/profesional/i) as HTMLSelectElement;
    expect(selectProfesional.disabled).toBe(true);
    expect(selectProfesional.value).toBe('10');
  });

  it('botón "Hoy" ajusta la fecha a la fecha actual en formato YYYY-MM-DD', () => {
    const onFiltrosChange = vi.fn();
    render(
      <FiltrosAgenda
        fecha="2026-01-01"
        profesionalId={null}
        sillonId={null}
        profesionales={profesionales}
        sillones={sillones}
        esRolProfesional={false}
        onFiltrosChange={onFiltrosChange}
      />
    );

    const botonHoy = screen.getByRole('button', { name: /hoy/i });
    fireEvent.click(botonHoy);

    const hoyEsperado = new Date().toISOString().split('T')[0];
    expect(onFiltrosChange).toHaveBeenCalledWith(
      expect.objectContaining({ fecha: hoyEsperado })
    );
  });
});
