import io
import json

import httpx
import pytest

USUARIO = {"nombre": "Prueba", "apellidos": "ASEE", "password": "SoloPruebas2027", "tipo": "cliente"}

# (servicio, método, ruta, cuerpo): operaciones de administración de cada servicio
RUTAS_ADMIN = [
    ("Espacios", "POST", "/api/espacios",
     {"nombre": "Auth", "tipo": "escenario", "ubicacion": "Norte", "capacidad": 10}),
    ("Espacios", "DELETE", "/api/espacios/99999", None),
    ("Escaleta", "POST", "/api/escaleta/artistas", {"nombre": "Auth"}),
    ("Escaleta", "DELETE", "/api/escaleta/99999", None),
    ("Merchandising", "PATCH", "/api/merchandising/1/stock", {"stock": 5}),
    ("Merchandising", "DELETE", "/api/merchandising/99999", None),
    ("Entradas", "POST", "/api/entradas/1/validar", None),
    ("Entradas", "DELETE", "/api/entradas/99999", None),
]


def usuario_de_tipo(modulo, monkeypatch, tipo):
    """Simula la respuesta de Usuarios a GET /usuarios/sesion."""
    def urllib_falso(peticion, **kwargs):
        assert peticion.full_url.endswith("/usuarios/sesion")
        return io.BytesIO(json.dumps({"id": 1, "tipo": tipo}).encode())

    def httpx_falso(url, **kwargs):
        assert url.endswith("/usuarios/sesion")
        return httpx.Response(200, json={"id": 1, "tipo": tipo})

    # Entradas consulta Usuarios con httpx; los demás servicios, con urllib.
    if hasattr(modulo, "httpx"):
        monkeypatch.setattr(modulo.httpx, "get", httpx_falso)
    if hasattr(modulo, "urlopen"):
        monkeypatch.setattr(modulo, "urlopen", urllib_falso)


@pytest.mark.parametrize("servicio_nombre,metodo,ruta,cuerpo", RUTAS_ADMIN)
def test_administracion_exige_administrador(servicio, monkeypatch, servicio_nombre, metodo, ruta, cuerpo):
    modulo, cliente = servicio(servicio_nombre)
    modulo.app.dependency_overrides.clear()  # protección real, sin administrador simulado
    cabecera = {"Authorization": "Bearer prueba"}
    with cliente:
        sin_sesion = cliente.request(metodo, ruta, json=cuerpo)
        assert sin_sesion.status_code == 401, sin_sesion.text
        assert sin_sesion.json()["codigo"] == 401

        usuario_de_tipo(modulo, monkeypatch, "cliente")
        como_cliente = cliente.request(metodo, ruta, json=cuerpo, headers=cabecera)
        assert como_cliente.status_code == 403, como_cliente.text

        usuario_de_tipo(modulo, monkeypatch, "administrador")
        como_admin = cliente.request(metodo, ruta, json=cuerpo, headers=cabecera)
        assert como_admin.status_code not in (401, 403), como_admin.text


def registrar(cliente, email):
    datos = dict(USUARIO, email=email)
    creado = cliente.post("/api/usuarios", json=datos)
    assert creado.status_code == 201, creado.text
    sesion = cliente.post("/api/usuarios/login", json={"email": email, "password": datos["password"]})
    assert sesion.status_code == 200, sesion.text
    return creado.json()["id"], {"Authorization": f"Bearer {sesion.json()['token']}"}


def test_usuarios_solo_propietario_o_admin(servicio):
    _, cliente = servicio("Usuarios")
    with cliente:
        ana, sesion_ana = registrar(cliente, "ana@example.test")
        luis, sesion_luis = registrar(cliente, "luis@example.test")
        cambio = {"nombre": "Nuevo", "apellidos": "Nombre", "email": "ana@example.test"}

        # Sin sesión
        assert cliente.put(f"/api/usuarios/{ana}", json=cambio).status_code == 401
        assert cliente.delete(f"/api/usuarios/{ana}").status_code == 401
        assert cliente.put(f"/api/usuarios/{ana}/foto", json={"url": "x"}).status_code == 401

        # Sesión de otro cliente
        assert cliente.put(f"/api/usuarios/{ana}", json=cambio, headers=sesion_luis).status_code == 403
        assert cliente.delete(f"/api/usuarios/{ana}", headers=sesion_luis).status_code == 403
        assert cliente.put(f"/api/usuarios/{ana}/foto", json={"url": "x"}, headers=sesion_luis).status_code == 403
        assert cliente.delete(f"/api/usuarios/{ana}/metodos-pago/1", headers=sesion_luis).status_code == 403

        # El propio usuario sí puede
        assert cliente.put(f"/api/usuarios/{ana}", json=cambio, headers=sesion_ana).status_code == 200
        assert cliente.put(f"/api/usuarios/{ana}/foto", json={"url": "x"}, headers=sesion_ana).status_code == 200
        assert cliente.delete(f"/api/usuarios/{ana}", headers=sesion_ana).status_code == 204
        assert cliente.get(f"/api/usuarios/{luis}").status_code == 200
