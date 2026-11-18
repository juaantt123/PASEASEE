import io
import json
from urllib.error import URLError

import httpx
import pytest

ESPACIO = {"nombre": "Prueba", "tipo": "escenario", "ubicacion": "Norte", "capacidad": 100}
FRANJA = {"fecha": "2027-07-16", "horaInicio": "21:00:00", "horaFin": "22:00:00"}
ACTUACION = dict(FRANJA, idArtista=8, idEspacio=1)
USUARIO = {"nombre": "Prueba", "apellidos": "ASEE", "email": "semana3@example.test",
           "password": "SoloPruebas2027", "tipo": "cliente"}
ENTRADA = {"idUsuario": 25, "idTipoEntrada": 1, "cantidad": 1, "idMetodoPago": 1}
MERCH = {"idUsuario": 25, "idProducto": 1, "cantidad": 1, "idMetodoPago": 1, "talla": "M"}


def estado(respuesta, esperado):
    assert respuesta.status_code == esperado, respuesta.text
    return respuesta.json()


@pytest.mark.parametrize("codigo", [200, 400, 404, 409])
def test_usuarios(servicio, codigo):
    _, cliente = servicio("Usuarios")
    with cliente:
        if codigo == 200:
            creado = estado(cliente.post("/api/usuarios", json=USUARIO), 201)
            obtenido = estado(cliente.get(f"/api/usuarios/{creado['id']}"), 200)
            assert obtenido["email"] == USUARIO["email"] and "password" not in obtenido
        elif codigo == 400:
            estado(cliente.post("/api/usuarios", json=dict(USUARIO, password="corta")), 400)
        elif codigo == 404:
            estado(cliente.get("/api/usuarios/99999"), 404)
        else:
            estado(cliente.post("/api/usuarios", json=USUARIO), 201)
            estado(cliente.post("/api/usuarios", json=USUARIO), 409)


@pytest.mark.parametrize("codigo", [200, 400, 404, 409, 503])
def test_espacios(servicio, monkeypatch, codigo):
    modulo, cliente = servicio("Espacios")

    def sin_escaleta(*args, **kwargs):
        raise URLError("Escaleta no disponible")

    monkeypatch.setattr(modulo, "urlopen", sin_escaleta)
    with cliente:
        if codigo == 200:
            creado = estado(cliente.post("/api/espacios", json=ESPACIO), 201)
            assert estado(cliente.get(f"/api/espacios/{creado['id']}"), 200)["capacidad"] == 100
        elif codigo == 400:
            estado(cliente.get("/api/espacios/disponibilidad", params=dict(FRANJA, horaFin="20:00:00")), 400)
        elif codigo == 404:
            estado(cliente.get("/api/espacios/99999"), 404)
        elif codigo == 409:
            estado(cliente.post("/api/espacios", json=ESPACIO), 201)
            estado(cliente.post("/api/espacios", json=ESPACIO), 409)
        else:
            estado(cliente.get("/api/espacios/disponibilidad", params=FRANJA), 503)


@pytest.mark.parametrize("codigo", [200, 400, 404, 409, 503])
def test_escaleta(servicio, monkeypatch, codigo):
    modulo, cliente = servicio("Escaleta")

    def espacio_remoto(*args, **kwargs):
        if codigo == 503:
            raise URLError("Espacios no disponible")
        datos = {"id": 1, "nombre": "Principal", "tipo": "escenario", "estado": "activo"}
        return io.BytesIO(json.dumps(datos).encode())

    monkeypatch.setattr(modulo, "urlopen", espacio_remoto)
    with cliente:
        if codigo == 200:
            creada = estado(cliente.post("/api/escaleta", json=ACTUACION), 201)
            assert estado(cliente.get("/api/escaleta", params={"idEspacio": 1}), 200) == [creada]
            assert creada["id"] == creada["idActuacion"]
        elif codigo == 400:
            estado(cliente.post("/api/escaleta", json=dict(ACTUACION, horaFin="20:00:00")), 400)
        elif codigo == 404:
            estado(cliente.post("/api/escaleta", json=dict(ACTUACION, idArtista=99999)), 404)
        elif codigo == 409:
            estado(cliente.post("/api/escaleta", json=ACTUACION), 201)
            estado(cliente.post("/api/escaleta", json=dict(ACTUACION, horaInicio="21:30:00")), 409)
            estado(cliente.post("/api/escaleta", json=dict(ACTUACION, horaInicio="22:00:00", horaFin="23:00:00")), 201)
        else:
            estado(cliente.post("/api/escaleta", json=ACTUACION), 503)
            assert estado(cliente.get("/api/escaleta"), 200) == []


@pytest.mark.parametrize("codigo", [200, 400, 404, 409, 503])
def test_entradas(servicio, monkeypatch, codigo):
    modulo, cliente = servicio("Entradas")

    def remoto(url, **kwargs):
        if codigo == 503:
            raise httpx.ConnectError("Usuarios no disponible", request=httpx.Request("GET", url))
        return httpx.Response(200, json=[{"id": 1}] if url.endswith("/metodos-pago") else {"id": 25})

    monkeypatch.setattr(modulo.httpx, "get", remoto)
    ruta = "/api/entradas/comprar"
    with cliente:
        if codigo == 200:
            compra = estado(cliente.post(ruta, json=ENTRADA), 201)
            assert estado(cliente.get(f"/api/entradas/compras/{compra['idCompra']}"), 200) == compra
            assert compra["precioTotal"] == 150
        else:
            cambios = {400: {"idMetodoPago": 2}, 404: {"idTipoEntrada": 99999},
                       409: {"cantidad": 1001}, 503: {}}[codigo]
            antes = estado(cliente.get("/api/entradas/1"), 200)["stockDisponible"]
            error = estado(cliente.post(ruta, json=dict(ENTRADA, **cambios)), codigo)
            assert error["codigo"] == codigo and error["mensaje"]
            assert estado(cliente.get("/api/entradas/1"), 200)["stockDisponible"] == antes


@pytest.mark.parametrize("codigo", [200, 400, 404, 409, 503])
def test_merchandising(servicio, monkeypatch, codigo):
    modulo, cliente = servicio("Merchandising")

    def remoto(url, **kwargs):
        if codigo == 503:
            raise URLError("Usuarios no disponible")
        datos = [{"id": 1}] if url.endswith("/metodos-pago") else {"id": 25}
        return io.BytesIO(json.dumps(datos).encode())

    monkeypatch.setattr(modulo, "urlopen", remoto)
    ruta = "/api/merchandising/compras"
    with cliente:
        if codigo == 200:
            compra = estado(cliente.post(ruta, json=MERCH), 201)
            assert estado(cliente.get(f"{ruta}/{compra['idCompra']}"), 200) == compra
            assert compra["precioTotal"] == 25
        else:
            cambios = {400: {"talla": None}, 404: {"idProducto": 99999},
                       409: {"cantidad": 301}, 503: {}}[codigo]
            antes = estado(cliente.get("/api/merchandising/1/stock"), 200)["stock"]
            estado(cliente.post(ruta, json=dict(MERCH, **cambios)), codigo)
            assert estado(cliente.get("/api/merchandising/1/stock"), 200)["stock"] == antes


@pytest.mark.parametrize("codigo", [200, 400, 404, 503])
def test_estadisticas(servicio, monkeypatch, codigo):
    modulo, cliente = servicio("Estadisticas")
    llamadas = []

    class SesionAdminFalsa:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def get(self, url, **kwargs):
            return httpx.Response(
                200, json={"id": 1, "tipo": "administrador"},
                request=httpx.Request("GET", url),
            )

    # Estadísticas comprueba el token contra Usuarios antes de ejecutar la ruta.
    monkeypatch.setattr(modulo.httpx, "AsyncClient", lambda **kwargs: SesionAdminFalsa())
    cliente.headers.update({"Authorization": "Bearer token-admin-de-prueba"})

    def origen(url, **kwargs):
        llamadas.append(url)
        if codigo == 404:
            assert url.endswith("/usuarios/99999")
            return httpx.Response(404, json={"codigo": 404})
        assert url.endswith("/usuarios")
        datos = [{"id": 1, "tipo": "cliente"}, {"id": 2, "tipo": "proveedor"}]
        return httpx.Response(200, json={"invalido": True} if codigo == 503 else datos)

    class SesionAdmin:
        """Sustituye la comprobación de sesión que Estadísticas hace en Usuarios."""
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, **kwargs):
            assert url.endswith("/usuarios/sesion")
            return httpx.Response(200, json={"id": 1, "tipo": "administrador"})

    monkeypatch.setattr(modulo.httpx, "get", origen)
    monkeypatch.setattr(modulo.httpx, "AsyncClient", SesionAdmin)
    admin = {"Authorization": "Bearer sesion-de-prueba"}
    with cliente:
        if codigo == 400:
            error = estado(cliente.get("/api/estadisticas/ingresos", headers=admin, params={
                "fechaInicio": "2027-07-18", "fechaFin": "2027-07-16",
            }), 400)
            assert not llamadas
        elif codigo == 404:
            error = estado(cliente.get("/api/recomendaciones/99999"), 404)
            assert len(llamadas) == 1
        else:
            error = estado(cliente.get("/api/estadisticas/usuarios", headers=admin), codigo)
        if codigo == 200:
            assert {k: error[k] for k in ("totalUsuarios", "clientes", "proveedores", "administradores")} == {
                "totalUsuarios": 2, "clientes": 1, "proveedores": 1, "administradores": 0,
            }
        else:
            assert error["codigo"] == codigo


def test_entradas_conserva_compra_al_reiniciar(servicio, monkeypatch):
    modulo, cliente = servicio("Entradas")

    def remoto(url, **kwargs):
        return httpx.Response(200, json=[{"id": 1}] if url.endswith("/metodos-pago") else {"id": 25})

    monkeypatch.setattr(modulo.httpx, "get", remoto)
    with cliente:
        stock = estado(cliente.get("/api/entradas/1"), 200)["stockDisponible"]
        compra = estado(cliente.post("/api/entradas/comprar", json=ENTRADA), 201)
    # Vuelve a ejecutar el ciclo de inicio del servicio con el mismo SQLite temporal.
    with cliente:
        assert estado(cliente.get(f"/api/entradas/compras/{compra['idCompra']}"), 200) == compra
        assert estado(cliente.get("/api/entradas/1"), 200)["stockDisponible"] == stock - 1
