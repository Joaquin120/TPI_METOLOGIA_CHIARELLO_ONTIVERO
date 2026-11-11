"""Tests unitarios para ServicioListaEspera (TDD task 2.1)."""

import pytest
from src.domain.lista_espera import ServicioListaEspera
from src.domain.models import EntradaListaEspera, EstadoListaEspera


class FakePuertoListaEspera:
    def __init__(self) -> None:
        self.entradas: dict[int, EntradaListaEspera] = {}
        self._next_id = 1

    def guardar(self, entrada: EntradaListaEspera) -> EntradaListaEspera:
        from dataclasses import replace

        guardada = replace(
            entrada,
            id=self._next_id,
            creado_en="2026-11-10 12:00:00",
        )
        self.entradas[self._next_id] = guardada
        self._next_id += 1
        return guardada

    def actualizar(self, entrada: EntradaListaEspera) -> EntradaListaEspera:
        if entrada.id not in self.entradas:
            raise ValueError("No existe")
        self.entradas[entrada.id] = entrada
        return entrada

    def obtener_por_id(self, entrada_id: int) -> EntradaListaEspera | None:
        return self.entradas.get(entrada_id)

    def listar(
        self,
        fecha: str | None = None,
        profesional_nombre: str | None = None,
        estado: str | None = None,
    ) -> list[EntradaListaEspera]:
        res = list(self.entradas.values())
        if fecha:
            res = [e for e in res if e.fecha_deseada == fecha]
        if profesional_nombre:
            res = [e for e in res if e.profesional_nombre == profesional_nombre]
        if estado:
            res = [e for e in res if e.estado == estado]
        return res

    def buscar_candidatos(
        self, fecha: str, profesional_nombre: str | None = None
    ) -> list[EntradaListaEspera]:
        res = [
            e
            for e in self.entradas.values()
            if e.fecha_deseada == fecha and e.estado == EstadoListaEspera.PENDIENTE
        ]
        if profesional_nombre:
            res = [
                e
                for e in res
                if e.profesional_nombre is None or e.profesional_nombre == profesional_nombre
            ]
        return sorted(res, key=lambda x: (x.creado_en or "", x.id or 0))


def test_registrar_solicitud_exitosa() -> None:
    puerto = FakePuertoListaEspera()
    servicio = ServicioListaEspera(puerto)

    entrada = servicio.registrar(
        paciente_nombre="Lucía Mendez",
        paciente_telefono="+5491122334455",
        fecha_deseada="2026-11-24",
        motivo="Revisión bracket despegado",
        profesional_nombre="Dr. Perez",
        franja_horaria="TARDE",
    )
    assert entrada.id == 1
    assert entrada.paciente_nombre == "Lucía Mendez"
    assert entrada.estado == EstadoListaEspera.PENDIENTE


def test_registrar_solicitud_validacion_campos_requeridos() -> None:
    puerto = FakePuertoListaEspera()
    servicio = ServicioListaEspera(puerto)

    with pytest.raises(ValueError, match="El nombre del paciente es obligatorio"):
        servicio.registrar(
            paciente_nombre="",
            paciente_telefono="+54911",
            fecha_deseada="2026-11-24",
            motivo="Dolor",
        )

    with pytest.raises(ValueError, match="El teléfono del paciente es obligatorio"):
        servicio.registrar(
            paciente_nombre="Paciente",
            paciente_telefono="",
            fecha_deseada="2026-11-24",
            motivo="Dolor",
        )

    with pytest.raises(ValueError, match="El motivo es obligatorio"):
        servicio.registrar(
            paciente_nombre="Paciente",
            paciente_telefono="+54911",
            fecha_deseada="2026-11-24",
            motivo="   ",
        )


def test_cancelar_entrada() -> None:
    puerto = FakePuertoListaEspera()
    servicio = ServicioListaEspera(puerto)

    entrada = servicio.registrar(
        paciente_nombre="Ana Frank",
        paciente_telefono="+5491155667788",
        fecha_deseada="2026-11-26",
        motivo="Consulta",
    )

    cancelada = servicio.cancelar(entrada.id)
    assert cancelada.estado == EstadoListaEspera.CANCELADO

    # Cancelar inexistente levanta error
    with pytest.raises(ValueError, match="Entrada no encontrada"):
        servicio.cancelar(999)


def test_buscar_candidatos_prioridad() -> None:
    puerto = FakePuertoListaEspera()
    servicio = ServicioListaEspera(puerto)

    e1 = servicio.registrar(
        paciente_nombre="Primero",
        paciente_telefono="+5491111111111",
        fecha_deseada="2026-11-27",
        motivo="Urgencia",
    )
    e2 = servicio.registrar(
        paciente_nombre="Segundo",
        paciente_telefono="+5491122222222",
        fecha_deseada="2026-11-27",
        motivo="Urgencia",
    )

    candidatos = servicio.buscar_candidatos(fecha="2026-11-27")
    assert len(candidatos) == 2
    assert candidatos[0].id == e1.id
    assert candidatos[1].id == e2.id


def test_marcar_notificado_y_asignado() -> None:
    puerto = FakePuertoListaEspera()
    servicio = ServicioListaEspera(puerto)

    entrada = servicio.registrar(
        paciente_nombre="Mario",
        paciente_telefono="+5491100000000",
        fecha_deseada="2026-11-28",
        motivo="Consulta",
    )

    notificada = servicio.marcar_notificado(entrada.id)
    assert notificada.estado == EstadoListaEspera.NOTIFICADO

    asignada = servicio.marcar_asignado(entrada.id)
    assert asignada.estado == EstadoListaEspera.ASIGNADO

    with pytest.raises(ValueError, match="Entrada no encontrada"):
        servicio.marcar_notificado(888)

    with pytest.raises(ValueError, match="Entrada no encontrada"):
        servicio.marcar_asignado(888)


def test_listar_filtros() -> None:
    puerto = FakePuertoListaEspera()
    servicio = ServicioListaEspera(puerto)

    servicio.registrar(
        paciente_nombre="A",
        paciente_telefono="1",
        fecha_deseada="2026-11-28",
        motivo="M1",
        profesional_nombre="Dr. Uno",
    )
    servicio.registrar(
        paciente_nombre="B",
        paciente_telefono="2",
        fecha_deseada="2026-11-29",
        motivo="M2",
        profesional_nombre="Dr. Dos",
    )

    assert len(servicio.listar(fecha="2026-11-28")) == 1
    assert len(servicio.listar(profesional_nombre="Dr. Dos")) == 1
    assert len(servicio.listar(estado=EstadoListaEspera.PENDIENTE)) == 2
