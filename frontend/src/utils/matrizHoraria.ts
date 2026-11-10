import { Turno, Bloqueo } from '../types';

export function horaAMinutos(hora: string): number {
  const [h, m] = hora.split(':').map(Number);
  return h * 60 + m;
}

export function minutosAHora(minutos: number): string {
  const h = Math.floor(minutos / 60);
  const m = minutos % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

export function generarFranjasHorarias(
  inicioStr: string = '08:00',
  finStr: string = '20:00',
  intervaloMinutos: number = 30
): string[] {
  const inicio = horaAMinutos(inicioStr);
  const fin = horaAMinutos(finStr);
  const franjas: string[] = [];

  for (let m = inicio; m < fin; m += intervaloMinutos) {
    franjas.push(minutosAHora(m));
  }

  return franjas;
}

export function turnoIntersecaFranja(
  horaInicioTurno: string,
  horaFinTurno: string,
  horaFranja: string,
  duracionFranjaMinutos: number = 30
): boolean {
  const inicioT = horaAMinutos(horaInicioTurno);
  const finT = horaAMinutos(horaFinTurno);
  const inicioF = horaAMinutos(horaFranja);
  const finF = inicioF + duracionFranjaMinutos;

  // Intersección de intervalos semiabiertos: max(inicioT, inicioF) < min(finT, finF)
  return Math.max(inicioT, inicioF) < Math.min(finT, finF);
}

export function buscarTurnoEnSlot(
  turnos: Turno[],
  recursoNombre: string,
  tipoRecurso: 'sillon' | 'profesional',
  horaSlot: string,
  duracionMinutos: number = 30
): Turno | undefined {
  return turnos.find((t) => {
    const coincideRecurso =
      tipoRecurso === 'sillon'
        ? t.sillon === recursoNombre
        : t.profesional === recursoNombre;

    return coincideRecurso && turnoIntersecaFranja(t.hora_inicio, t.hora_fin, horaSlot, duracionMinutos);
  });
}

export function buscarBloqueoEnSlot(
  bloqueos: Bloqueo[],
  sillonId: number,
  fechaStr: string,
  horaSlot: string,
  duracionMinutos: number = 30
): Bloqueo | undefined {
  const inicioSlotDt = new Date(`${fechaStr}T${horaSlot}:00`);
  const finSlotMin = horaAMinutos(horaSlot) + duracionMinutos;
  const finSlotHora = minutosAHora(finSlotMin);
  const finSlotDt = new Date(`${fechaStr}T${finSlotHora}:00`);

  return bloqueos.find((b) => {
    if (b.sillon_id !== sillonId) return false;
    const inicioB = new Date(b.fecha_hora_inicio);
    const finB = new Date(b.fecha_hora_fin);

    return Math.max(inicioB.getTime(), inicioSlotDt.getTime()) < Math.min(finB.getTime(), finSlotDt.getTime());
  });
}

