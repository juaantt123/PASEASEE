from datetime import datetime, timezone
import json
import os
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


app = FastAPI(
    title="API Merchandising - Subsonic Festival",
    description="Gestión de los productos de merchandising del festival",
    version="1.0.0"
)

CategoriaProducto = Literal[
    "camiseta", "sudadera", "accesorio", "poster", "otros"
]
TallaProducto = Literal["XS", "S", "M", "L", "XL", "XXL"]
EstadoCompra = Literal["realizada", "preparada", "entregada", "cancelada"]

# Categorías para las que es obligatorio indicar la talla al comprar
CATEGORIAS_CON_TALLA = ("camiseta", "sudadera")


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
# DATOS PROVISIONALES
# ==========================================

productos = [
    Producto(
        id=1,
        nombre="Camiseta oficial Subsonic 2027",
        descripcion="Camiseta de algodón con el cartel de la edición.",
        categoria="camiseta",
        precio=25.0,
        stock=300,
        imagen="camiseta_oficial.png",
        disponible=True
    ),
    Producto(
        id=2,
        nombre="Sudadera Subsonic Night",
        descripcion="Sudadera con capucha y logotipo reflectante.",
        categoria="sudadera",
        precio=45.0,
        stock=120,
        imagen="sudadera_night.png",
        disponible=True
    ),
    Producto(
        id=3,
        nombre="Póster conmemorativo",
        descripcion="Póster numerado de la edición 2027.",
        categoria="poster",
        precio=12.0,
        stock=0,
        imagen="poster_2027.png",
        disponible=False
    )
]

compras = []


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
# FUNCIONES AUXILIARES
# ==========================================

def buscar_producto(idProducto: int):
    for producto in productos:
        if producto.id == idProducto:
            return producto

    raise HTTPException(
        status_code=404,
        detail="Producto no encontrado"
    )


def buscar_compra(idCompra: int):
    for compra in compras:
        if compra.idCompra == idCompra:
            return compra

    raise HTTPException(
        status_code=404,
        detail="Compra no encontrada"
    )


def actualizar_disponibilidad(producto: Producto):
    """El campo disponible no se almacena, se deduce del stock."""
    producto.disponible = producto.stock > 0
    return producto


def comprobar_duplicado(nombre: str, categoria: str, excluir_id=None):
    """Un producto se considera repetido si coinciden nombre y categoría."""
    for producto in productos:
        if (
            producto.nombre.strip().lower() == nombre.strip().lower()
            and producto.categoria == categoria
            and producto.id != excluir_id
        ):
            raise HTTPException(
                status_code=409,
                detail="Ya existe un producto con esos datos"
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
    resultado = productos

    if categoria is not None:
        resultado = [p for p in resultado if p.categoria == categoria]

    if disponible is not None:
        resultado = [p for p in resultado if p.disponible == disponible]

    return resultado


# POST /api/merchandising
@app.post("/api/merchandising", response_model=Producto, status_code=201)
def crear_producto(datos: ProductoInput):
    comprobar_duplicado(datos.nombre, datos.categoria)

    nuevo_id = max((p.id for p in productos), default=0) + 1

    nuevo = Producto(
        id=nuevo_id,
        **datos.model_dump(),
        disponible=datos.stock > 0
    )

    productos.append(nuevo)
    return nuevo


# ==========================================
# RUTAS FIJAS
# Se declaran antes que /api/merchandising/{idProducto}
# para que no se interpreten como un identificador
# ==========================================

# GET /api/merchandising/disponibles
@app.get("/api/merchandising/disponibles", response_model=list[Producto])
def productos_disponibles():
    return [p for p in productos if p.stock > 0]


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

    # Comprobar el producto
    producto = buscar_producto(datos.idProducto)

    # La talla solo se exige en las categorías que la necesitan
    if producto.categoria in CATEGORIAS_CON_TALLA and datos.talla is None:
        raise HTTPException(
            status_code=400,
            detail="Es necesario indicar la talla para este producto"
        )

    if producto.categoria not in CATEGORIAS_CON_TALLA and datos.talla is not None:
        raise HTTPException(
            status_code=400,
            detail="Este producto no admite talla"
        )

    # Comprobar el stock disponible
    if producto.stock < datos.cantidad:
        raise HTTPException(
            status_code=409,
            detail="No hay suficiente stock disponible"
        )

    # Descontar el stock reservado para la compra
    producto.stock = producto.stock - datos.cantidad
    actualizar_disponibilidad(producto)

    nuevo_id = max((c.idCompra for c in compras), default=0) + 1

    nueva_compra = CompraMerchandising(
        idCompra=nuevo_id,
        idUsuario=datos.idUsuario,
        idProducto=datos.idProducto,
        cantidad=datos.cantidad,
        talla=datos.talla,
        precioTotal=round(producto.precio * datos.cantidad, 2),
        fechaCompra=datetime.now(timezone.utc),
        estado="realizada"
    )

    compras.append(nueva_compra)
    return nueva_compra


# GET /api/merchandising/compras/{idCompra}
@app.get(
    "/api/merchandising/compras/{idCompra}",
    response_model=CompraMerchandising
)
def obtener_compra(idCompra: int):
    return buscar_compra(idCompra)


# PATCH /api/merchandising/compras/{idCompra}/cancelar
@app.patch(
    "/api/merchandising/compras/{idCompra}/cancelar",
    response_model=CompraMerchandising
)
def cancelar_compra(idCompra: int):
    compra = buscar_compra(idCompra)

    if compra.estado == "cancelada":
        raise HTTPException(
            status_code=409,
            detail="La compra ya está cancelada"
        )

    if compra.estado == "entregada":
        raise HTTPException(
            status_code=409,
            detail="Una compra entregada no puede cancelarse"
        )

    compra.estado = "cancelada"

    # Devolver el stock al producto
    for producto in productos:
        if producto.id == compra.idProducto:
            producto.stock = producto.stock + compra.cantidad
            actualizar_disponibilidad(producto)
            break

    return compra


# GET /api/merchandising/usuarios/{idUsuario}/compras
@app.get(
    "/api/merchandising/usuarios/{idUsuario}/compras",
    response_model=list[CompraMerchandising]
)
def compras_del_usuario(idUsuario: int):
    # Comprobar en Usuarios que el usuario existe
    comprobar_usuario(idUsuario)

    return [c for c in compras if c.idUsuario == idUsuario]


# ==========================================
# CONSULTA Y MODIFICACIÓN DE UN PRODUCTO
# ==========================================

# GET /api/merchandising/{idProducto}
@app.get("/api/merchandising/{idProducto}", response_model=Producto)
def obtener_producto(idProducto: int):
    return buscar_producto(idProducto)


# PUT /api/merchandising/{idProducto}
@app.put("/api/merchandising/{idProducto}", response_model=Producto)
def modificar_producto(idProducto: int, datos: ProductoInput):
    producto = buscar_producto(idProducto)

    # El contrato no define un 409 para esta operación,
    # por lo que aquí no se comprueban productos repetidos.

    for campo, valor in datos.model_dump().items():
        setattr(producto, campo, valor)

    actualizar_disponibilidad(producto)
    return producto


# DELETE /api/merchandising/{idProducto}
@app.delete("/api/merchandising/{idProducto}", status_code=204)
def eliminar_producto(idProducto: int):
    producto = buscar_producto(idProducto)

    if any(c.idProducto == idProducto for c in compras):
        raise HTTPException(
            status_code=409,
            detail="El producto tiene compras asociadas"
        )

    productos.remove(producto)
    return None


# ==========================================
# GESTIÓN DEL STOCK
# ==========================================

# GET /api/merchandising/{idProducto}/stock
@app.get("/api/merchandising/{idProducto}/stock", response_model=Stock)
def obtener_stock(idProducto: int):
    producto = buscar_producto(idProducto)

    return Stock(
        idProducto=producto.id,
        stock=producto.stock,
        disponible=producto.stock > 0
    )


# PATCH /api/merchandising/{idProducto}/stock
@app.patch("/api/merchandising/{idProducto}/stock", response_model=Stock)
def actualizar_stock(idProducto: int, datos: ActualizacionStock):
    producto = buscar_producto(idProducto)

    producto.stock = datos.stock
    actualizar_disponibilidad(producto)

    return Stock(
        idProducto=producto.id,
        stock=producto.stock,
        disponible=producto.disponible
    )
