from datetime import datetime
import json
import os
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


app = FastAPI(
    title="API Merchandising - Subsonic Festival",
    description="Gestión de los productos de merchandising del festival",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

CategoriaProducto = Literal[
    "camiseta", "sudadera", "accesorio", "poster", "otros"
]
TallaProducto = Literal["XS", "S", "M", "L", "XL", "XXL"]
EstadoCompra = Literal["realizada", "preparada", "entregada", "cancelada"]

# ==========================================
# MODELOS DE DATOS SEGÚN EL YAML
# ==========================================

class ProductoInput(BaseModel):
    nombre: str = Field(min_length=1)
    descripcion: str | None = None
    categoria: CategoriaProducto
    precio: float = Field(ge=0)
    stock: int = Field(ge=0)
    imagen: str | None = None


class Producto(ProductoInput):
    id: int
    disponible: bool


class Stock(BaseModel):
    idProducto: int
    stock: int = Field(ge=0)
    disponible: bool


class ActualizacionStock(BaseModel):
    stock: int = Field(ge=0)


class CompraMerchandisingInput(BaseModel):
    idUsuario: int
    idProducto: int
    cantidad: int = Field(ge=1)
    talla: TallaProducto | None = None
    idMetodoPago: int


class CompraMerchandising(BaseModel):
    idCompra: int
    idUsuario: int
    idProducto: int
    cantidad: int
    talla: str | None = None
    precioTotal: float
    fechaCompra: datetime
    estado: EstadoCompra


class Error(BaseModel):
    codigo: int
    mensaje: str


# ==========================================
# PERSISTENCIA (SQLite)
# ==========================================

try:
    from . import persistencia_merch as persistencia
except ImportError:
    import persistencia_merch as persistencia

persistencia.inicializar()


# ==========================================
# COMUNICACIÓN CON EL SERVICIO USUARIOS
# ==========================================

# URL base del servicio Usuarios. Debe incluir el prefijo /api.
USUARIOS_URL = os.getenv("USUARIOS_URL", "http://localhost:8001/api").rstrip("/")
TIMEOUT_USUARIOS = float(os.getenv("USUARIOS_TIMEOUT", "3"))


def llamada_usuarios(ruta: str):
    """Consulta síncrona al servicio Usuarios.

    Devuelve los datos recibidos, None si Usuarios responde 404
    y lanza un 503 si el servicio no está disponible.
    """
    url = f"{USUARIOS_URL}{ruta}"
    try:
        with urlopen(url, timeout=TIMEOUT_USUARIOS) as respuesta:
            return json.loads(respuesta.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            return None
        raise HTTPException(
            status_code=503,
            detail="El servicio Usuarios no está disponible"
        ) from exc
    except (URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        raise HTTPException(
            status_code=503,
            detail="El servicio Usuarios no está disponible"
        ) from exc


def comprobar_usuario(idUsuario: int):
    """Comprueba en Usuarios que el usuario existe."""
    usuario = llamada_usuarios(f"/usuarios/{idUsuario}")

    if usuario is None:
        raise HTTPException(
            status_code=404,
            detail="Usuario no encontrado"
        )

    return usuario


def comprobar_metodo_pago(idUsuario: int, idMetodoPago: int):
    """Comprueba que el método de pago pertenece al usuario."""
    metodos = llamada_usuarios(f"/usuarios/{idUsuario}/metodos-pago")

    if metodos is None:
        raise HTTPException(
            status_code=404,
            detail="Usuario no encontrado"
        )

    for metodo in metodos:
        if metodo.get("id") == idMetodoPago:
            return metodo

    raise HTTPException(
        status_code=400,
        detail="El método de pago no pertenece al usuario"
    )


# ==========================================
# VALIDACIÓN DE ERRORES
# ==========================================

@app.exception_handler(RequestValidationError)
async def error_validacion(request, exc):
    return JSONResponse(
        status_code=400,
        content={"codigo": 400, "mensaje": "Datos o parámetros no válidos"}
    )


@app.exception_handler(HTTPException)
async def error_http(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"codigo": exc.status_code, "mensaje": exc.detail}
    )


# ==========================================
# COMPROBAR MICROSERVICIO
# ==========================================

@app.get("/")
def inicio():
    return {"mensaje": "Microservicio Merchandising funcionando"}


# ==========================================
# GESTIÓN DE PRODUCTOS
# ==========================================

# GET /api/merchandising
@app.get("/api/merchandising", response_model=list[Producto])
def listar_productos(
    categoria: CategoriaProducto | None = None,
    disponible: bool | None = None
):
    return persistencia.listar_productos(categoria, disponible)


# POST /api/merchandising
@app.post("/api/merchandising", response_model=Producto, status_code=201)
def crear_producto(datos: ProductoInput):
    return persistencia.crear_producto(datos.model_dump())


# ==========================================
# RUTAS FIJAS
# Se declaran antes que /api/merchandising/{idProducto}
# para que no se interpreten como un identificador
# ==========================================

# GET /api/merchandising/disponibles
@app.get("/api/merchandising/disponibles", response_model=list[Producto])
def productos_disponibles():
    return persistencia.listar_productos(disponible=True)


# ==========================================
# GESTIÓN DE COMPRAS
# ==========================================

# POST /api/merchandising/compras
@app.post(
    "/api/merchandising/compras",
    response_model=CompraMerchandising,
    status_code=201
)
def comprar_producto(datos: CompraMerchandisingInput):
    # Comprobar en Usuarios que el comprador existe
    comprobar_usuario(datos.idUsuario)

    # Comprobar que el método de pago es suyo
    comprobar_metodo_pago(datos.idUsuario, datos.idMetodoPago)

    # Producto, talla y stock se validan y descuentan en una sola transacción
    return persistencia.registrar_compra(
        datos.idUsuario, datos.idProducto, datos.cantidad, datos.talla
    )


# GET /api/merchandising/compras/{idCompra}
@app.get(
    "/api/merchandising/compras/{idCompra}",
    response_model=CompraMerchandising
)
def obtener_compra(idCompra: int):
    return persistencia.obtener_compra(idCompra)


# PATCH /api/merchandising/compras/{idCompra}/cancelar
@app.patch(
    "/api/merchandising/compras/{idCompra}/cancelar",
    response_model=CompraMerchandising
)
def cancelar_compra(idCompra: int):
    return persistencia.cancelar_compra(idCompra)


# GET /api/merchandising/usuarios/{idUsuario}/compras
@app.get(
    "/api/merchandising/usuarios/{idUsuario}/compras",
    response_model=list[CompraMerchandising]
)
def compras_del_usuario(idUsuario: int):
    # Comprobar en Usuarios que el usuario existe
    comprobar_usuario(idUsuario)

    return persistencia.compras_de_usuario(idUsuario)


# ==========================================
# CONSULTA Y MODIFICACIÓN DE UN PRODUCTO
# ==========================================

# GET /api/merchandising/{idProducto}
@app.get("/api/merchandising/{idProducto}", response_model=Producto)
def obtener_producto(idProducto: int):
    return persistencia.obtener_producto(idProducto)


# PUT /api/merchandising/{idProducto}
@app.put("/api/merchandising/{idProducto}", response_model=Producto)
def modificar_producto(idProducto: int, datos: ProductoInput):
    # El contrato no define un 409 para esta operación,
    # por lo que aquí no se comprueban productos repetidos.
    return persistencia.modificar_producto(idProducto, datos.model_dump())


# DELETE /api/merchandising/{idProducto}
@app.delete("/api/merchandising/{idProducto}", status_code=204)
def eliminar_producto(idProducto: int):
    persistencia.eliminar_producto(idProducto)
    return None


# ==========================================
# GESTIÓN DEL STOCK
# ==========================================

# GET /api/merchandising/{idProducto}/stock
@app.get("/api/merchandising/{idProducto}/stock", response_model=Stock)
def obtener_stock(idProducto: int):
    producto = persistencia.obtener_producto(idProducto)

    return Stock(
        idProducto=producto["id"],
        stock=producto["stock"],
        disponible=producto["disponible"]
    )


# PATCH /api/merchandising/{idProducto}/stock
@app.patch("/api/merchandising/{idProducto}/stock", response_model=Stock)
def actualizar_stock(idProducto: int, datos: ActualizacionStock):
    producto = persistencia.actualizar_stock(idProducto, datos.stock)

    return Stock(
        idProducto=producto["id"],
        stock=producto["stock"],
        disponible=producto["disponible"]
    )
