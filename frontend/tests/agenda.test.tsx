import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { Agenda } from '../src/pages/Agenda';
import * as TurnosApi from '../src/api/turnos';
import * as RecursosApi from '../src/api/recursos';
import * as PacientesApi from '../src/api/pacientes';
import { AuthContext } from '../src/context/AuthContext';
import { Usuario, Turno, Profesional, Sillon, Paciente } from '../src/types';

describe('Página Agenda (Integración y Flujos Operativos)', () => {
  const usuarioAdmin: Usuario = {
    id: 1,
    email: 'admin@clinica.com',
    rol: 'Administrador',
    tenant_id: 1,
  };

  const usuarioProfesional: Usuario = {
    id: 2,
    email: 'dra.silva@clinica.com',
    rol: 'Profesional',
    tenant_id: 1,
    profesional_id: 20,
  };

  const mockProfesionales: Profesional[] = [
    { id: 10, nombre: 'Dr. Lopez', activo: true },
    { id: 20, nombre: 'Dra. Silva', activo: true },
  ];

  const mockSillones: Sillon[] = [
    { id: 1, nombre: 'Sillón Principal', activo: true },
    { id: 2, nombre: 'Sillón Secundario', activo: true },
  ];

  const mockPacientes: Paciente[] = [
    { id: 101, tenant_id: 1, dni: '11223344', nombre: 'Juan Perez', telefono: '12345678' },
  ];

  const mockTurnos: Turno[] = [
    {
      id: 1,
      paciente: 'Juan Perez',
      profesional: 'Dr. Lopez',
      sillon: 'Sillón Principal',
      fecha: '2026-11-10',
      hora_inicio: '09:00',
      hora_fin: '09:30',
      estado: 'PENDIENTE',
    },
    {
      id: 2,
      paciente: 'Ana Martinez',
      profesional: 'Dra. Silva',
      sillon: 'Sillón Secundario',
      fecha: '2026-11-10',
      hora_inicio: '10:00',
      hora_fin: '10:45',
      estado: 'CONFIRMADO',
    },
  ];

  const renderAgendaConUsuario = (usuario: Usuario) => {
    return render(
      <AuthContext.Provider
        value={{
          usuario,
          estaAutenticado: true,
          cargando: false,
          token: 'token-valido',
          iniciarSesion: vi.fn(),
          cerrarSesion: vi.fn(),
        }}
      >
        <Agenda />
      </AuthContext.Provider>
    );
  };

  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(RecursosApi, 'listarProfesionales').mockResolvedValue(mockProfesionales);
    vi.spyOn(RecursosApi, 'listarSillones').mockResolvedValue(mockSillones);
    vi.spyOn(PacientesApi, 'listarPacientes').mockResolvedValue(mockPacientes);
    vi.spyOn(TurnosApi, 'listarTurnos').mockResolvedValue(mockTurnos);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renderiza la vista y carga la lista cronológica de turnos para el día', async () => {
    renderAgendaConUsuario(usuarioAdmin);

    expect(screen.getByTestId('page-agenda')).toBeInTheDocument();
    expect(await screen.findByText('Juan Perez')).toBeInTheDocument();
    expect(screen.getByText('Ana Martinez')).toBeInTheDocument();
    expect(screen.getByText('09:00 - 09:30')).toBeInTheDocument();
    expect(screen.getByText('10:00 - 10:45')).toBeInTheDocument();
  });

  it('bloquea el selector de profesional al ID del usuario cuando el rol es Profesional', async () => {
    renderAgendaConUsuario(usuarioProfesional);

    await screen.findByText('Ana Martinez');

    const selectProf = screen.getByLabelText(/profesional/i) as HTMLSelectElement;
    expect(selectProf.disabled).toBe(true);
    expect(selectProf.value).toBe('20');
  });

  it('permite cambiar estado a CONFIRMADO en un turno PENDIENTE', async () => {
    const confirmarSpy = vi.spyOn(TurnosApi, 'confirmarTurno').mockResolvedValue({
      ...mockTurnos[0],
      estado: 'CONFIRMADO',
    });

    renderAgendaConUsuario(usuarioAdmin);
    await screen.findByText('Juan Perez');

    const btnConfirmar = screen.getByRole('button', { name: /confirmar/i });
    fireEvent.click(btnConfirmar);

    await waitFor(() => {
      expect(confirmarSpy).toHaveBeenCalledWith(1);
    });
  });

  it('permite completar un turno CONFIRMADO', async () => {
    const completarSpy = vi.spyOn(TurnosApi, 'completarTurno').mockResolvedValue({
      ...mockTurnos[1],
      estado: 'COMPLETADO',
    });

    renderAgendaConUsuario(usuarioAdmin);
    await screen.findByText('Ana Martinez');

    const btnCompletar = screen.getByRole('button', { name: /completar/i });
    fireEvent.click(btnCompletar);

    await waitFor(() => {
      expect(completarSpy).toHaveBeenCalledWith(2);
    });
  });

  it('permite cancelar un turno activo', async () => {
    const cancelarSpy = vi.spyOn(TurnosApi, 'cancelarTurno').mockResolvedValue({
      ...mockTurnos[0],
      estado: 'CANCELADO',
    });

    renderAgendaConUsuario(usuarioAdmin);
    await screen.findByText('Juan Perez');

    const btnsCancelar = screen.getAllByRole('button', { name: /cancelar/i });
    fireEvent.click(btnsCancelar[0]);

    await waitFor(() => {
      expect(cancelarSpy).toHaveBeenCalledWith(1);
    });
  });

  it('abre el modal de nuevo turno y crea el turno refrescando la grilla', async () => {
    const crearSpy = vi.spyOn(TurnosApi, 'crearTurno').mockResolvedValue({
      id: 3,
      paciente: 'Nuevo Paciente',
      profesional: 'Dr. Lopez',
      sillon: 'Sillón Principal',
      fecha: '2026-11-10',
      hora_inicio: '11:00',
      hora_fin: '11:30',
      estado: 'PENDIENTE',
    });

    renderAgendaConUsuario(usuarioAdmin);
    await screen.findByText('Juan Perez');

    const btnNuevoTurno = screen.getByRole('button', { name: /nuevo turno/i });
    fireEvent.click(btnNuevoTurno);

    expect(screen.getByRole('dialog')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/paciente/i), {
      target: { value: 'Nuevo Paciente' },
    });
    fireEvent.change(screen.getByLabelText(/hora inicio/i), {
      target: { value: '11:00' },
    });
    fireEvent.change(screen.getByLabelText(/hora fin/i), {
      target: { value: '11:30' },
    });

    fireEvent.click(screen.getByRole('button', { name: /agendar turno/i }));

    await waitFor(() => {
      expect(crearSpy).toHaveBeenCalled();
    });
  });

  it('permite alternar entre vista de lista y vista matricial', async () => {
    renderAgendaConUsuario(usuarioAdmin);
    await screen.findByText('Juan Perez');

    const btnMatriz = screen.getByRole('button', { name: /^matriz$/i });
    fireEvent.click(btnMatriz);

    expect(await screen.findByRole('columnheader', { name: /sillón principal/i })).toBeInTheDocument();
    expect(screen.getByText(/vista matricial de atención/i)).toBeInTheDocument();

    const btnLista = screen.getByRole('button', { name: /^lista$/i });
    fireEvent.click(btnLista);

    expect(await screen.findByText('Juan Perez')).toBeInTheDocument();
  });

  it('clic en celda libre de la matriz abre modal preseleccionando recurso y franja', async () => {
    renderAgendaConUsuario(usuarioAdmin);
    await screen.findByText('Juan Perez');

    fireEvent.click(screen.getByRole('button', { name: /^matriz$/i }));
    await screen.findByRole('columnheader', { name: /sillón principal/i });

    const slotLibre = screen.getByTestId('slot-Sillón Principal-08:00');
    fireEvent.click(slotLibre);

    const dialog = screen.getByRole('dialog');
    expect(dialog).toBeInTheDocument();

    const inputInicio = within(dialog).getByLabelText(/hora inicio/i) as HTMLInputElement;
    expect(inputInicio.value).toBe('08:00');

    const selectSillon = within(dialog).getByLabelText(/sillón/i) as HTMLSelectElement;
    expect(selectSillon.value).toBe('Sillón Principal');
  });
});
