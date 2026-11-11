"""Tests unitarios para modelos y puertos de Lista de Espera (TDD task 1.1)."""

from src.domain.models import EntradaListaEspera, EstadoListaEspera
from src.domain.puertos import PuertoListaEspera


def test_modelo_entrada_lista_espera_instanciacion() -> None:
    """Verifica atributos e inmutabilidad de EntradaListaEspera."""
    entrada = EntradaListaEspera(
        tenant_id=1,
        paciente_nombre="Paciente Espera Uno",
        paciente_telefono="+5491188887777",
        fecha_deseada="2026-11-25",
        motivo="Consulta de conducto",
        profesional_nombre="Dr. Ejemplo",
        franja_horaria="MAÑANA",
        estado=EstadoListaEspera.PENDIENTE,
        creado_en="2026-11-10 10:00:00",
        id=10,
    )
    assert entrada.id == 10
    assert entrada.tenant_id == 1
    assert entrada.paciente_nombre == "Paciente Espera Uno"
    assert entrada.profesional_nombre == "Dr. Ejemplo"
    assert entrada.estado == EstadoListaEspera.PENDIENTE
    assert entrada.franja_horaria == "MAÑANA"


def test_puerto_lista_espera_runtime_checkable() -> None:
    """Verifica que PuertoListaEspera actúe como Protocol runtime_checkable."""

    class MockValido:
        def guardar(self, entrada: EntradaListaEspera) -> EntradaListaEspera:
            return entrada

        def actualizar(self, entrada: EntradaListaEspera) -> EntradaListaEspera:
            return entrada

        def obtener_por_id(self, entrada_id: int) -> EntradaListaEspera | None:
            return None

        def listar(
            self,
            fecha: str | None = None,
            profesional_nombre: str | None = None,
            estado: str | None = None,
        ) -> list[EntradaListaEspera]:
            return []

        def buscar_candidatos(
            self, fecha: str, profesional_nombre: str | None = None
        ) -> list[EntradaListaEspera]:
            return []

    class MockInvalido:
        pass

    assert isinstance(MockValido(), PuertoListaEspera)
    assert not isinstance(MockInvalido(), PuertoListaEspera)

