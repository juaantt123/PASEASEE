from datetime import date, datetime, timezone
from typing import Literal
import os
import httpx

from fastapi import FastAPI, Header, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator

app = FastAPI(title="API Entradas - Subsonic Festival", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["null"],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
)
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



try:
    from .rutas_sqlite import configurar
except ImportError:
    from rutas_sqlite import configurar

configurar(app, (TipoEntrada, TipoEntradaInput, CompraEntrada, CompraEntradaInput, EntradaUsuario, ValidacionEntrada, EstadoEntrada, TipoNombre, EstadoTipo), consultar_usuarios, URL_USUARIOS)
