import pytest

from scripts.probar_e2e import FLUJOS, comprobar_resumen, plataforma

pytestmark = pytest.mark.integracion


@pytest.fixture(scope="module")
def pedir():
    with plataforma() as cliente:
        yield cliente


@pytest.mark.parametrize("nombre", list(FLUJOS))
def test_intercambio_http_real(pedir, nombre):
    FLUJOS[nombre](pedir)


def test_resumen_global(pedir):
    comprobar_resumen(pedir)
