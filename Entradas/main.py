from datetime import date
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator


app = FastAPI(
    title="API Entradas - Subsonic Festival",
    description="Gestión de entradas del festival",
    version="1.0.0"
)

TipoNombre = Literal["vip", "abono_completo", "abono_un_dia"]
EstadoTipo = Literal["disponible", "agotada"]


# Modelos de datos según el YAML
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
            raise ValueError(
                "La fecha final no puede ser anterior a la inicial"
            )
        return self


class TipoEntrada(TipoEntradaInput):
    id: int
    stockDisponible: int = Field(ge=0)
    estado: EstadoTipo


# Datos provisionales
tipos_entrada = [
    TipoEntrada(
        id=1,
        nombre="vip",
        descripcion="Acceso VIP al festival",
        precio=150,
        stockTotal=1000,
        stockDisponible=1000,
        fechaInicioValidez=date(2027, 7, 15),
        fechaFinValidez=date(2027, 7, 18),
        estado="disponible"
    ),
    TipoEntrada(
        id=2,
        nombre="abono_completo",
        descripcion="Acceso durante todos los días",
        precio=90,
        stockTotal=5000,
        stockDisponible=5000,
        fechaInicioValidez=date(2027, 7, 15),
        fechaFinValidez=date(2027, 7, 18),
        estado="disponible"
    )
]

# Se utilizará al implementar las compras
compras = []


def buscar_tipo(idTipoEntrada: int):
    for entrada in tipos_entrada:
        if entrada.id == idTipoEntrada:
            return entrada

    raise HTTPException(
        status_code=404,
        detail="Tipo de entrada no encontrado"
    )


def comprobar_nombre(nombre: str, excluir_id=None):
    for entrada in tipos_entrada:
        if entrada.nombre == nombre and entrada.id != excluir_id:
            raise HTTPException(
                status_code=409,
                detail="Ya existe ese tipo de entrada"
            )


# Adaptar errores de validación al código 400 del YAML
@app.exception_handler(RequestValidationError)
async def error_validacion(request, exc):
    return JSONResponse(
        status_code=400,
        content={
            "codigo": 400,
            "mensaje": "Datos o parámetros no válidos"
        }
    )


@app.get("/")
def inicio():
    return {"mensaje": "Microservicio de Entradas funcionando"}


# GET /api/entradas
@app.get("/api/entradas", response_model=list[TipoEntrada])
def listar_entradas(
    tipo: TipoNombre | None = None,
    estado: EstadoTipo | None = None
):
    resultado = tipos_entrada

    if tipo is not None:
        resultado = [e for e in resultado if e.nombre == tipo]

    if estado is not None:
        resultado = [e for e in resultado if e.estado == estado]

    return resultado


# POST /api/entradas
@app.post(
    "/api/entradas",
    response_model=TipoEntrada,
    status_code=201
)
def crear_tipo_entrada(datos: TipoEntradaInput):
    comprobar_nombre(datos.nombre)

    nuevo_id = max(
        (e.id for e in tipos_entrada),
        default=0
    ) + 1

    nueva = TipoEntrada(
        id=nuevo_id,
        **datos.model_dump(),
        stockDisponible=datos.stockTotal,
        estado="disponible"
    )

    tipos_entrada.append(nueva)
    return nueva


# GET /api/entradas/disponibles
@app.get(
    "/api/entradas/disponibles",
    response_model=list[TipoEntrada]
)
def entradas_disponibles():
    return [
        e for e in tipos_entrada
        if e.stockDisponible > 0
    ]


# GET /api/entradas/tipo/{tipo}
@app.get(
    "/api/entradas/tipo/{tipo}",
    response_model=TipoEntrada
)
def obtener_por_tipo(tipo: TipoNombre):
    for entrada in tipos_entrada:
        if entrada.nombre == tipo:
            return entrada

    raise HTTPException(
        status_code=404,
        detail="Tipo de entrada no encontrado"
    )


# GET /api/entradas/{idTipoEntrada}
@app.get(
    "/api/entradas/{idTipoEntrada}",
    response_model=TipoEntrada
)
def obtener_tipo_entrada(idTipoEntrada: int):
    return buscar_tipo(idTipoEntrada)


# PUT /api/entradas/{idTipoEntrada}
@app.put(
    "/api/entradas/{idTipoEntrada}",
    response_model=TipoEntrada
)
def modificar_tipo_entrada(
    idTipoEntrada: int,
    datos: TipoEntradaInput
):
    entrada = buscar_tipo(idTipoEntrada)
    comprobar_nombre(datos.nombre, excluir_id=idTipoEntrada)

    vendidas = entrada.stockTotal - entrada.stockDisponible

    if datos.stockTotal < vendidas:
        raise HTTPException(
            status_code=400,
            detail="El stock total no puede ser menor que las entradas vendidas"
        )

    for campo, valor in datos.model_dump().items():
        setattr(entrada, campo, valor)

    entrada.stockDisponible = datos.stockTotal - vendidas
    entrada.estado = (
        "disponible" if entrada.stockDisponible > 0
        else "agotada"
    )

    return entrada


# DELETE /api/entradas/{idTipoEntrada}
@app.delete(
    "/api/entradas/{idTipoEntrada}",
    status_code=204
)
def eliminar_tipo_entrada(idTipoEntrada: int):
    entrada = buscar_tipo(idTipoEntrada)

    if any(
        c["idTipoEntrada"] == idTipoEntrada
        for c in compras
    ):
        raise HTTPException(
            status_code=409,
            detail="Existen compras asociadas"
        )

    tipos_entrada.remove(entrada)
    return None
