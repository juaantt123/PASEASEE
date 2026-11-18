"""Arranca los servicios locales y verifica flujos HTTP. Ejecutar: python scripts/probar_e2e.py."""
import os
from contextlib import ExitStack, contextmanager
from pathlib import Path
import socket
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
from uuid import uuid4

import httpx

RAIZ = Path(__file__).resolve().parents[1]
MODULOS = {
    "Usuarios": "Usuarios.main_usuario",
    "Escaleta": "Escaleta.main_escaleta",
    "Espacios": "Espacios.main_espacios",
    "Entradas": "Entradas.main_entradas",
    "Merchandising": "Merchandising.main_tienda",
    "Estadisticas": "Estadisticas.main_estadisticas",
}


def puertos_locales():
    # Reserva todos a la vez para que ningún servicio reciba el mismo puerto.
    with ExitStack() as pila:
        puertos = {}
        for nombre in MODULOS:
            s = pila.enter_context(socket.socket())
            s.bind(("127.0.0.1", 0))
            puertos[nombre] = s.getsockname()[1]
    return puertos


def detener(proceso):
    if proceso.poll() is None:
        proceso.terminate()
        try:
            proceso.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proceso.kill()
            proceso.wait(timeout=5)


def esperar(servicio, proceso, url, log, cliente):
    limite = time.monotonic() + 15
    while time.monotonic() < limite and proceso.poll() is None:
        try:
            if cliente.get(url, timeout=0.5).status_code == 200 and proceso.poll() is None:
                return
        except httpx.RequestError:
            pass
        time.sleep(0.05)
    raise RuntimeError(f"No arrancó {servicio}:\n{log.read_text(encoding='utf-8', errors='replace')}")


@contextmanager
def plataforma():
    puertos = puertos_locales()
    urls = {nombre: f"http://127.0.0.1:{puerto}" for nombre, puerto in puertos.items()}
    with TemporaryDirectory(prefix="asee-e2e-") as temporal, ExitStack() as pila:
        temp = Path(temporal)
        cliente = pila.enter_context(httpx.Client(timeout=10, trust_env=False))
        # Las dependencias de los servicios originales también usan clientes HTTP.
        local = {k: v for k, v in os.environ.items()
                 if k.lower() not in {"http_proxy", "https_proxy", "all_proxy"}}
        env = dict(local, NO_PROXY="127.0.0.1,localhost", no_proxy="127.0.0.1,localhost",
                   PYTHONIOENCODING="utf-8",
                   ESCALETA_DB=str(temp / "escaleta.sqlite3"),
                   ENTRADAS_DB=str(temp / "entradas.sqlite3"),
                   MERCHANDISING_DB=str(temp / "merchandising.sqlite3"),
                   USUARIOS_DB=str(temp / "usuarios.sqlite3"),
                   ESPACIOS_DB=str(temp / "espacios.sqlite3"),
                   CLAVE_INTERNA_ESTADISTICAS="clave-temporal-pruebas",
                   ESCALETA_URL=urls["Escaleta"] + "/api",
                   ESPACIOS_URL=urls["Espacios"] + "/api",
                   URL_USUARIOS=urls["Usuarios"] + "/api",
                   USUARIOS_URL=urls["Usuarios"] + "/api",
                   URL_ENTRADAS=urls["Entradas"] + "/api",
                   URL_ESPACIOS=urls["Espacios"] + "/api",
                   URL_ESCALETA=urls["Escaleta"] + "/api",
                   URL_MERCHANDISING=urls["Merchandising"] + "/api")
        for nombre, puerto in puertos.items():
            log = temp / f"{nombre}.log"
            with log.open("wb") as salida:
                proceso = subprocess.Popen(
                    [sys.executable, "-m", "uvicorn", f"{MODULOS[nombre]}:app",
                     "--host", "127.0.0.1", "--port", str(puerto)],
                    cwd=RAIZ, env=env, stdout=salida, stderr=subprocess.STDOUT,
                )
            pila.callback(detener, proceso)
            esperar(nombre, proceso, urls[nombre], log, cliente)

        # Las operaciones de administración y Estadísticas requieren sesión de administrador.
        login = cliente.post(urls["Usuarios"] + "/api/usuarios/login",
                             json={"email": "admin@subsonic.com", "password": "admin12345"})
        login.raise_for_status()
        admin = {"Authorization": f"Bearer {login.json()['token']}"}

        def pedir(servicio, metodo, ruta, codigo=200, **kwargs):
            requiere_admin = servicio == "Estadisticas" or (
                servicio == "Escaleta" and metodo.upper() in {"POST", "PUT", "PATCH", "DELETE"}
            ) or (
                servicio == "Entradas" and (
                    metodo.upper() == "PUT" or ruta.endswith("/validar")
                )
            )
            if requiere_admin:
                kwargs["headers"] = {**admin, **kwargs.get("headers", {})}
            respuesta = cliente.request(metodo, urls[servicio] + "/api" + ruta, **kwargs)
            if codigo is None:
                return respuesta
            if respuesta.status_code != codigo:
                raise AssertionError(
                    f"{servicio} {metodo} {ruta}: se esperaba {codigo}, "
                    f"se recibió {respuesta.status_code}: {respuesta.text}\n"
                    f"Registro de {servicio}:\n"
                    f"{(temp / (servicio + '.log')).read_text(encoding='utf-8', errors='replace')[-6000:]}"
                )
            return respuesta.json() if respuesta.content else None

        yield pedir


def registrar(pedir):
    perfil = {"nombre": "Cliente", "apellidos": "Pruebas ASEE", "tipo": "cliente",
              "email": f"{uuid4().hex}@example.test", "password": "SoloPruebas2027"}
    usuario = pedir("Usuarios", "POST", "/usuarios", 201, json=perfil)
    pago = pedir("Usuarios", "POST", f"/usuarios/{usuario['id']}/metodos-pago", 201,
                 json={"tipo": "paypal"})
    sesion = pedir("Usuarios", "POST", "/usuarios/login", json={
        "email": perfil["email"], "password": perfil["password"],
    })
    return usuario["id"], pago["id"], {"Authorization": f"Bearer {sesion['token']}"}


def flujo_entradas(pedir):
    usuario, pago, sesion = registrar(pedir)
    inicial = pedir("Entradas", "GET", "/entradas/1")
    carga = dict(idUsuario=usuario, idTipoEntrada=1, cantidad=2, idMetodoPago=pago)
    pedir("Entradas", "POST", "/entradas/comprar", 400, json=dict(carga, idMetodoPago=pago + 500))
    assert pedir("Entradas", "GET", "/entradas/1")["stockDisponible"] == inicial["stockDisponible"]
    compra = pedir("Entradas", "POST", "/entradas/comprar", 201, json=carga)
    assert compra["estado"] == "completada" and compra["precioTotal"] == inicial["precio"] * 2
    assert pedir("Entradas", "GET", f"/entradas/compras/{compra['idCompra']}") == compra
    assert pedir("Entradas", "GET", "/entradas/1")["stockDisponible"] == inicial["stockDisponible"] - 2
    pedir("Entradas", "GET", f"/entradas/usuarios/{usuario}", 401)
    otro, _, _ = registrar(pedir)
    pedir("Entradas", "GET", f"/entradas/usuarios/{otro}", 403, headers=sesion)
    entradas = pedir("Entradas", "GET", f"/entradas/usuarios/{usuario}", headers=sesion)
    assert len(entradas) == 2 and len({e["codigo"] for e in entradas}) == 2
    assert all(e["estado"] == "valida" and e["idUsuario"] == usuario for e in entradas)
    assert pedir("Entradas", "POST", f"/entradas/{entradas[0]['idEntrada']}/validar")["valida"]
    pedir("Entradas", "POST", f"/entradas/{entradas[0]['idEntrada']}/validar", 409)
    pedir("Entradas", "PATCH", f"/entradas/{entradas[1]['idEntrada']}/cancelar")
    assert pedir("Entradas", "GET", "/entradas/1")["stockDisponible"] == inicial["stockDisponible"] - 1


def comprar_merchandising(pedir, usuario, pago):
    return pedir("Merchandising", "POST", "/merchandising/compras", 201, json={
        "idUsuario": usuario, "idProducto": 1, "cantidad": 2, "idMetodoPago": pago, "talla": "M",
    })


def flujo_merchandising(pedir):
    usuario, pago, _ = registrar(pedir)
    stock = "/merchandising/1/stock"
    inicial = pedir("Merchandising", "GET", stock)["stock"]
    compra = comprar_merchandising(pedir, usuario, pago)
    assert compra["precioTotal"] == 50 and compra["estado"] == "realizada"
    assert pedir("Merchandising", "GET", stock)["stock"] == inicial - 2
    lista = pedir("Merchandising", "GET", f"/merchandising/usuarios/{usuario}/compras")
    assert lista == [compra]
    ruta = f"/merchandising/compras/{compra['idCompra']}/cancelar"
    assert pedir("Merchandising", "PATCH", ruta)["estado"] == "cancelada"
    pedir("Merchandising", "PATCH", ruta, 409)
    assert pedir("Merchandising", "GET", stock)["stock"] == inicial


def flujo_disponibilidad(pedir):
    fecha = {"fecha": "2027-07-16", "horaInicio": "21:00:00", "horaFin": "22:00:00"}

    def disponibilidad():
        objetos = pedir("Espacios", "GET", "/espacios/disponibilidad",
                       params=dict(fecha, tipo="escenario"))
        return next(e["disponible"] for e in objetos if e["idEspacio"] == 1)

    assert disponibilidad() is True
    datos = dict(fecha, idArtista=8, idEspacio=1)
    actuacion = pedir("Escaleta", "POST", "/escaleta", 201, json=datos)
    assert actuacion["nombreEspacio"] == "Escenario Principal"
    pedir("Escaleta", "POST", "/escaleta", 409, json=datos)
    eventos = pedir("Espacios", "GET", "/espacios/1/actuaciones")
    assert [e["idActuacion"] for e in eventos] == [actuacion["id"]]
    assert disponibilidad() is False
    uso = pedir("Estadisticas", "GET", "/estadisticas/espacios")
    escenario = next(e for e in uso if e["idEspacio"] == 1)
    assert escenario["numeroEventos"] == 1 and escenario["horasUso"] == 1
    pedir("Escaleta", "PUT", f"/escaleta/{actuacion['id']}", json=dict(datos, estado="cancelada"))
    assert disponibilidad() is True
    uso = pedir("Estadisticas", "GET", "/estadisticas/espacios")
    assert next(e for e in uso if e["idEspacio"] == 1)["numeroEventos"] == 0


def flujo_estadisticas(pedir):
    usuarios = "/estadisticas/usuarios"
    ventas = "/estadisticas/merchandising"
    inicial = pedir("Estadisticas", "GET", usuarios)
    base = pedir("Estadisticas", "GET", ventas)
    usuario, pago, _ = registrar(pedir)
    actual = pedir("Estadisticas", "GET", usuarios)
    assert actual["totalUsuarios"] == inicial["totalUsuarios"] + 1
    assert actual["clientes"] == inicial["clientes"] + 1
    compra = comprar_merchandising(pedir, usuario, pago)
    actual = pedir("Estadisticas", "GET", ventas)
    assert actual["productosVendidos"] == base["productosVendidos"] + compra["cantidad"]
    assert actual["ingresos"] == base["ingresos"] + compra["precioTotal"]
    producto = pedir("Merchandising", "GET", "/merchandising/1")
    assert actual["productoMasVendido"] == producto["nombre"]
    pedir("Merchandising", "PATCH", f"/merchandising/compras/{compra['idCompra']}/cancelar")
    assert pedir("Estadisticas", "GET", ventas) == base


FLUJOS = {
    "Compra y validación de entradas": flujo_entradas,
    "Compra y cancelación de merchandising": flujo_merchandising,
    "Disponibilidad Espacios ↔ Escaleta": flujo_disponibilidad,
    "Estadísticas de usuarios y merchandising": flujo_estadisticas,
}


def comprobar_resumen(pedir):
    ruta = "/estadisticas/resumen"
    antes = pedir("Estadisticas", "GET", ruta)
    ruta_diaria = "/estadisticas/ventas-por-dia"
    diarias_antes = {v["fecha"]: v for v in pedir("Estadisticas", "GET", ruta_diaria)}
    usuario, pago, sesion = registrar(pedir)
    tipo = pedir("Entradas", "GET", "/entradas/1")
    compra = pedir("Entradas", "POST", "/entradas/comprar", 201, json={
        "idUsuario": usuario, "idTipoEntrada": tipo["id"], "cantidad": 2,
        "idMetodoPago": pago,
    })
    dia = compra["fechaCompra"][:10]
    periodo = {"fechaInicio": dia, "fechaFin": dia}
    base_diaria = diarias_antes.get(dia, {"numeroVentas": 0, "ingresos": 0.0})
    # La venta debe conservar el precio original aunque luego cambie el catálogo.
    campos = ("nombre", "descripcion", "stockTotal", "fechaInicioValidez", "fechaFinValidez")
    cambios = {k: tipo[k] for k in campos} | {"precio": tipo["precio"] + 10}
    pedir("Entradas", "PUT", "/entradas/1", json=cambios)

    actual = pedir("Estadisticas", "GET", ruta)
    assert actual["totalUsuarios"] == antes["totalUsuarios"] + 1
    assert actual["totalEspacios"] == antes["totalEspacios"]
    assert actual["entradasVendidas"] == antes["entradasVendidas"] + 2
    assert actual["ingresosTotales"] == round(antes["ingresosTotales"] + compra["precioTotal"], 2)

    assert pedir("Estadisticas", "GET", ruta_diaria, params=periodo) == [{
        "fecha": dia, "numeroVentas": base_diaria["numeroVentas"] + 1,
        "ingresos": round(base_diaria["ingresos"] + compra["precioTotal"], 2),
    }]

    privadas = f"/entradas/usuarios/{usuario}"
    pedir("Entradas", "GET", privadas, 401)
    entradas = pedir("Entradas", "GET", privadas, headers=sesion)
    pedir("Entradas", "PATCH", f"/entradas/{entradas[0]['idEntrada']}/cancelar")

    actual = pedir("Estadisticas", "GET", ruta)
    assert actual["entradasVendidas"] == antes["entradasVendidas"] + 1
    assert actual["ingresosTotales"] == round(antes["ingresosTotales"] + tipo["precio"], 2)
    ventas = pedir("Estadisticas", "GET", "/estadisticas/entradas", params=periodo)
    ingresos = pedir("Estadisticas", "GET", "/estadisticas/ingresos", params=periodo)
    assert ventas["ingresos"] == ingresos["ingresosEntradas"]
    assert pedir("Estadisticas", "GET", ruta_diaria, params=periodo) == [{
        "fecha": dia, "numeroVentas": base_diaria["numeroVentas"] + 1,
        "ingresos": round(base_diaria["ingresos"] + tipo["precio"], 2),
    }]
    assert pedir("Estadisticas", "GET", "/estadisticas/entradas", params={
        "fechaInicio": "2000-01-01", "fechaFin": "2000-01-01",
    })["totalVendidas"] == 0

    pedir("Entradas", "PATCH", f"/entradas/{entradas[1]['idEntrada']}/cancelar")
    assert pedir("Estadisticas", "GET", ruta)["entradasVendidas"] == antes["entradasVendidas"]
    assert pedir("Estadisticas", "GET", ruta)["ingresosTotales"] == antes["ingresosTotales"]
    esperadas = [diarias_antes[dia]] if dia in diarias_antes else []
    assert pedir("Estadisticas", "GET", ruta_diaria, params=periodo) == esperadas


def main():
    with plataforma() as pedir:
        for nombre, flujo in FLUJOS.items():
            flujo(pedir)
            print(f"OK - {nombre}")
        comprobar_resumen(pedir)
        print("OK - Resumen global de Estadísticas")
    print("5 flujos extremo a extremo comprobados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
