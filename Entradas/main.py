from datetime import date, datetime, timezone
from threading import Lock
from typing import Literal
import os
import httpx

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator

app = FastAPI(title="API Entradas - Subsonic Festival", version="1.0.0")
URL_USUARIOS = os.getenv("URL_USUARIOS", "http://127.0.0.1:8001/api")
TipoNombre = Literal["vip", "abono_completo", "abono_un_dia"]
EstadoTipo = Literal["disponible", "agotada"]
EstadoIndividual = Literal["valida", "utilizada", "cancelada"]


# MODELOS DEL YAML
class TipoEntradaInput(BaseModel):
    nombre: TipoNombre
    descripcion: str = ""
    precio: float = Field(ge=0)
    stockTotal: int = Field(ge=1)
    fechaInicioValidez: date
    fechaFinValidez: date

    @model_validator(mode="after")
    def validar_fechas(self):
        if self.fechaFinValidez < self.fechaInicioValidez:
            raise ValueError("La fecha final no puede ser anterior a la inicial")
        return self


class TipoEntrada(TipoEntradaInput):
    id: int
    stockDisponible: int = Field(ge=0)
    estado: EstadoTipo


class CompraEntradaInput(BaseModel):
    idUsuario: int = Field(gt=0)
    idTipoEntrada: int = Field(gt=0)
    cantidad: int = Field(ge=1)
    idMetodoPago: int = Field(gt=0)


class CompraEntrada(BaseModel):
    idCompra: int
    idUsuario: int
    idTipoEntrada: int
    tipoEntrada: TipoNombre
    cantidad: int
    precioTotal: float
    fechaCompra: datetime
    estado: Literal["completada", "cancelada"]


class EntradaUsuario(BaseModel):
    idEntrada: int
    idUsuario: int
    idTipoEntrada: int
    tipoEntrada: TipoNombre
    codigo: str
    fechaCompra: datetime
    fechaInicioValidez: date
    fechaFinValidez: date
    estado: EstadoIndividual


class ValidacionEntrada(BaseModel):
    idEntrada: int
    valida: bool
    fechaValidacion: datetime | None = None
    mensaje: str


class EstadoEntrada(BaseModel):
    idEntrada: int
    tipoEntrada: TipoNombre
    estado: EstadoIndividual

# DATOS TEMPORALES: se pierden al reiniciar el servidor
# Solo pruebas: no existe un cobro real ni persistencia.
tipos_entrada: list[TipoEntrada] = [
    TipoEntrada(
        id=1, nombre="vip", descripcion="Acceso VIP al festival",
        precio=150, stockTotal=1000, stockDisponible=1000,
        fechaInicioValidez=date(2027, 7, 15),
        fechaFinValidez=date(2027, 7, 18), estado="disponible"
    ),
    TipoEntrada(
        id=2, nombre="abono_completo", descripcion="Acceso todos los dias",
        precio=90, stockTotal=5000, stockDisponible=5000,
        fechaInicioValidez=date(2027, 7, 15),
        fechaFinValidez=date(2027, 7, 18), estado="disponible"
    )
]
compras: list[CompraEntrada] = []
entradas_usuarios: list[EntradaUsuario] = []
# Mapeo interno para relacionar las entradas individuales con su compra.
entrada_a_compra: dict[int, int] = {}
contador_tipos = 3
contador_compras = 1
contador_entradas = 1
bloqueo = Lock()  # Protege los datos en memoria dentro de un solo proceso.


# FUNCIONES AUXILIARES
def buscar_tipo(id_tipo: int) -> TipoEntrada:
    for tipo in tipos_entrada:
        if tipo.id == id_tipo:
            return tipo
    raise HTTPException(404, "Tipo de entrada no encontrado")


def buscar_entrada(id_entrada: int) -> EntradaUsuario:
    for entrada in entradas_usuarios:
        if entrada.idEntrada == id_entrada:
            return entrada
    raise HTTPException(404, "Entrada no encontrada")


def comprobar_nombre(nombre: str, excluir_id: int | None = None):
    if any(t.nombre == nombre and t.id != excluir_id for t in tipos_entrada):
        raise HTTPException(409, "Ya existe ese tipo de entrada")


def consultar_usuarios(id_usuario: int, id_pago: int | None = None):
    try:
        usuario = httpx.get(f"{URL_USUARIOS}/usuarios/{id_usuario}", timeout=5)
        if usuario.status_code == 404:
            raise HTTPException(404, "Usuario no encontrado")
        if usuario.status_code != 200:
            raise HTTPException(503, "No se puede consultar Usuarios")
        if id_pago is not None:
            respuesta = httpx.get(
                f"{URL_USUARIOS}/usuarios/{id_usuario}/metodos-pago", timeout=5
            )
            if respuesta.status_code == 404:
                raise HTTPException(404, "Usuario no encontrado")
            if respuesta.status_code != 200:
                raise HTTPException(503, "No se pueden consultar los metodos de pago")
            metodos = respuesta.json()
            if not isinstance(metodos, list):
                raise ValueError("Respuesta de metodos de pago incorrecta")
            if not any(m.get("id") == id_pago for m in metodos):
                raise HTTPException(400, "El metodo de pago no pertenece al usuario")
    except (httpx.RequestError, ValueError, KeyError, TypeError, AttributeError):
        raise HTTPException(503, "Microservicio Usuarios no disponible")


@app.exception_handler(RequestValidationError)
async def error_validacion(request, exc):
    return JSONResponse(status_code=400, content={"codigo": 400, "mensaje": "Datos o parametros no validos"})

    return JSONResponse(status_code=exc.status_code, content={"codigo": exc.status_code, "mensaje": str(exc.detail)})


@app.get("/")
def inicio():
    return {"mensaje": "Microservicio Entradas funcionando"}


# TIPOS DE ENTRADA
@app.get("/api/entradas", response_model=list[TipoEntrada])
def listar_entradas(tipo: TipoNombre | None = None, estado: EstadoTipo | None = None):
    return [t for t in tipos_entrada if (tipo is None or t.nombre == tipo) and (estado is None or t.estado == estado)]


@app.post("/api/entradas", response_model=TipoEntrada, status_code=201)
def crear_tipo(datos: TipoEntradaInput):
    global contador_tipos
    with bloqueo:
        comprobar_nombre(datos.nombre)
        nuevo = TipoEntrada(
            id=contador_tipos, **datos.model_dump(),
            stockDisponible=datos.stockTotal, estado="disponible"
        )
        contador_tipos += 1
        tipos_entrada.append(nuevo)
        return nuevo


# IMPORTANTE: rutas especificas antes de /api/entradas/{idTipoEntrada}
@app.get("/api/entradas/disponibles", response_model=list[TipoEntrada])
def listar_disponibles():
    return [t for t in tipos_entrada if t.stockDisponible > 0]


@app.get("/api/entradas/tipo/{tipo}", response_model=TipoEntrada)
def obtener_por_tipo(tipo: TipoNombre):
    for entrada in tipos_entrada:
        if entrada.nombre == tipo:
            return entrada
    raise HTTPException(404, "Tipo de entrada no encontrado")


# COMPRAS E INTEGRACION CON USUARIOS
@app.post("/api/entradas/comprar", response_model=CompraEntrada, status_code=201)
def comprar_entradas(datos: CompraEntradaInput):
    global contador_compras, contador_entradas

    # Primero se valida la existencia del usuario y del metodo de pago.
    consultar_usuarios(datos.idUsuario, datos.idMetodoPago)

    with bloqueo:
        tipo = buscar_tipo(datos.idTipoEntrada)
        if tipo.stockDisponible < datos.cantidad:
            raise HTTPException(409, "No hay suficientes entradas disponibles")

        ahora = datetime.now(timezone.utc)
        compra = CompraEntrada(
            idCompra=contador_compras,
            idUsuario=datos.idUsuario,
            idTipoEntrada=tipo.id,
            tipoEntrada=tipo.nombre,
            cantidad=datos.cantidad,
            precioTotal=round(tipo.precio * datos.cantidad, 2),
            fechaCompra=ahora,
            estado="completada"
        )
        contador_compras += 1
        nuevas = []
        for _ in range(datos.cantidad):
            ident = contador_entradas
            contador_entradas += 1
            nuevas.append(EntradaUsuario(
                idEntrada=ident,
                idUsuario=datos.idUsuario,
                idTipoEntrada=tipo.id,
                tipoEntrada=tipo.nombre,
                codigo=f"SUB-2027-{ident:06d}",
                fechaCompra=ahora,
                fechaInicioValidez=tipo.fechaInicioValidez,
                fechaFinValidez=tipo.fechaFinValidez,
                estado="valida"
            ))
            entrada_a_compra[ident] = compra.idCompra

        compras.append(compra)
        entradas_usuarios.extend(nuevas)
        tipo.stockDisponible -= datos.cantidad
        tipo.estado = "disponible" if tipo.stockDisponible else "agotada"
        return compra

@app.get("/api/entradas/usuarios/{idUsuario}", response_model=list[EntradaUsuario])
def entradas_de_usuario(idUsuario: int):
    consultar_usuarios(idUsuario)
    return [e for e in entradas_usuarios if e.idUsuario == idUsuario]


@app.get("/api/entradas/compras/{idCompra}", response_model=CompraEntrada)
def obtener_compra(idCompra: int):
    for compra in compras:
        if compra.idCompra == idCompra:
            return compra
    raise HTTPException(404, "Compra no encontrada")


# OPERACIONES SOBRE ENTRADAS INDIVIDUALES
@app.patch("/api/entradas/{idEntrada}/cancelar", response_model=EntradaUsuario)
def cancelar_entrada(idEntrada: int):
    with bloqueo:
        entrada = buscar_entrada(idEntrada)
        if entrada.estado != "valida":
            raise HTTPException(409, "La entrada no se puede cancelar")
        entrada.estado = "cancelada"
        tipo = buscar_tipo(entrada.idTipoEntrada)
        tipo.stockDisponible += 1
        tipo.estado = "disponible"

        # La compra se marca cancelada solo si todas sus entradas lo estan.
        id_compra = entrada_a_compra.get(idEntrada)
        asociadas = [e for e in entradas_usuarios if entrada_a_compra.get(e.idEntrada) == id_compra]
        if id_compra is not None and asociadas and all(e.estado == "cancelada" for e in asociadas):
            for compra in compras:
                if compra.idCompra == id_compra:
                    compra.estado = "cancelada"
                    break
        return entrada


@app.post("/api/entradas/{idEntrada}/validar", response_model=ValidacionEntrada)
def validar_entrada(idEntrada: int):
    with bloqueo:
        entrada = buscar_entrada(idEntrada)
        if entrada.estado != "valida":
            raise HTTPException(409, "Entrada cancelada o ya utilizada")
        # Este prototipo comprueba el estado; no controla el reloj del festival.
        entrada.estado = "utilizada"
        return ValidacionEntrada(
            idEntrada=idEntrada,
            valida=True,
            fechaValidacion=datetime.now(timezone.utc),
            mensaje="Entrada valida. Acceso permitido."
        )

@app.get("/api/entradas/{idEntrada}/estado", response_model=EstadoEntrada)
def consultar_estado(idEntrada: int):
    entrada = buscar_entrada(idEntrada)
    return EstadoEntrada(idEntrada=entrada.idEntrada, tipoEntrada=entrada.tipoEntrada, estado=entrada.estado)


# RUTAS GENERICAS AL FINAL
@app.get("/api/entradas/{idTipoEntrada}", response_model=TipoEntrada)
def obtener_tipo(idTipoEntrada: int):
    return buscar_tipo(idTipoEntrada)


@app.put("/api/entradas/{idTipoEntrada}", response_model=TipoEntrada)
def modificar_tipo(idTipoEntrada: int, datos: TipoEntradaInput):
    with bloqueo:
        entrada = buscar_tipo(idTipoEntrada)
        comprobar_nombre(datos.nombre, excluir_id=idTipoEntrada)
        vendidas_net = entrada.stockTotal - entrada.stockDisponible
        if datos.stockTotal < vendidas_net:
            raise HTTPException(400, "El stock total no puede ser menor que las entradas vendidas")
        for campo, valor in datos.model_dump().items():
            setattr(entrada, campo, valor)
        entrada.stockDisponible = datos.stockTotal - vendidas_net
        entrada.estado = "disponible" if entrada.stockDisponible else "agotada"
        return entrada


@app.delete("/api/entradas/{idTipoEntrada}", status_code=204)
def eliminar_tipo(idTipoEntrada: int):
    with bloqueo:
        entrada = buscar_tipo(idTipoEntrada)
        if any(c.idTipoEntrada == idTipoEntrada for c in compras):
            raise HTTPException(409, "Existen compras asociadas")
        tipos_entrada.remove(entrada)
        return None
