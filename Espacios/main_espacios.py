from datetime import date, time
import json
import os
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request as PeticionHTTP, urlopen

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


app = FastAPI(
    title="API Espacios - Subsonic Festival",
    description="Gestión de los espacios del festival",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TipoEspacio = Literal[
    "escenario", "restauracion", "descanso", "servicios",
    "merchandising", "comida", "tienda_ropa", "tatuador", "otros"
]
EstadoEspacio = Literal["activo", "libre", "ocupado", "mantenimiento", "cerrado"]


# Modelos de datos según el YAML
class EspacioInput(BaseModel):
    nombre: str = Field(min_length=1)
    tipo: TipoEspacio
    ubicacion: str = Field(min_length=1)
    capacidad: int = Field(default=1, ge=1)
    tamano: int = Field(default=1, ge=1)
    descripcion: str | None = None
    estado: EstadoEspacio = "activo"


class Espacio(EspacioInput):
    id: int


class ActualizacionEstado(BaseModel):
    estado: EstadoEspacio


class ActualizacionCapacidad(BaseModel):
    capacidad: int = Field(ge=1)


class DisponibilidadEspacio(BaseModel):
    idEspacio: int
    nombreEspacio: str
    fecha: date
    horaInicio: time
    horaFin: time
    disponible: bool
    motivo: str | None = None


class ActuacionEspacio(BaseModel):
    idActuacion: int
    idArtista: int | None = None
    nombreArtista: str | None = None
    fecha: date
    horaInicio: time
    horaFin: time


class Error(BaseModel):
    codigo: int
    mensaje: str


try:
    from . import persistencia_espacios as persistencia
except ImportError:
    import persistencia_espacios as persistencia

persistencia.inicializar(Espacio)

# URL base del servicio Escaleta. Debe incluir el prefijo /api.
ESCALETA_URL = os.getenv("ESCALETA_URL", "http://localhost:8002/api").rstrip("/")
TIMEOUT_ESCALETA = float(os.getenv("ESCALETA_TIMEOUT", "3"))


def buscar_espacio(idEspacio: int):
    espacio = persistencia.obtener(idEspacio, Espacio)
    if espacio is None:
        raise HTTPException(status_code=404, detail="Espacio no encontrado")
    return espacio


def llamada_escaleta(ruta: str, parametros: dict | None = None):
    url = f"{ESCALETA_URL}{ruta}"
    if parametros:
        url = f"{url}?{urlencode(parametros)}"
    try:
        with urlopen(url, timeout=TIMEOUT_ESCALETA) as respuesta:
            return json.loads(respuesta.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            return []
        raise HTTPException(
            status_code=503,
            detail="El servicio Escaleta no está disponible"
        ) from exc
    except (URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        raise HTTPException(
            status_code=503,
            detail="El servicio Escaleta no está disponible"
        ) from exc


USUARIOS_URL = os.getenv("USUARIOS_URL", "http://127.0.0.1:8001/api").rstrip("/")


def exigir_admin(authorization: str | None = Header(default=None)):
    """Solo un administrador con sesión válida en Usuarios puede modificar datos."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Inicia sesión como administrador")
    peticion = PeticionHTTP(
        f"{USUARIOS_URL}/usuarios/sesion", headers={"Authorization": authorization}
    )
    try:
        with urlopen(peticion, timeout=3) as respuesta:
            usuario = json.loads(respuesta.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise HTTPException(status_code=401, detail="La sesión no es válida") from exc
        raise HTTPException(status_code=503, detail="No se puede verificar la sesión") from exc
    except (URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        raise HTTPException(status_code=503, detail="No se puede verificar la sesión") from exc
    if usuario.get("tipo") != "administrador":
        raise HTTPException(status_code=403, detail="Acceso exclusivo para administradores")


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


@app.get("/")
def inicio():
    return {"mensaje": "Microservicio Espacios funcionando"}


# GET /api/espacios
@app.get("/api/espacios", response_model=list[Espacio])
def listar_espacios(
    tipo: TipoEspacio | None = None,
    estado: EstadoEspacio | None = None
):
    return persistencia.listar(Espacio, tipo, estado)


# GET /api/espacios/activos
@app.get("/api/espacios/activos", response_model=list[Espacio])
def espacios_activos():
    return [e for e in persistencia.listar(Espacio) if e.estado in {"activo", "libre"}]


# GET /api/espacios/disponibilidad
@app.get(
    "/api/espacios/disponibilidad",
    response_model=list[DisponibilidadEspacio]
)
def consultar_disponibilidad(
    fecha: date,
    horaInicio: time,
    horaFin: time,
    tipo: TipoEspacio | None = None
):
    if horaFin <= horaInicio:
        raise HTTPException(
            status_code=400,
            detail="La hora de fin debe ser posterior a la hora de inicio"
        )

    actuaciones = llamada_escaleta("/escaleta", {"fecha": fecha.isoformat()})
    if not isinstance(actuaciones, list):
        raise HTTPException(status_code=503, detail="Respuesta no válida de Escaleta")

    resultado = []
    candidatos = [e for e in persistencia.listar(Espacio) if e.estado in {"activo", "libre"}]
    if tipo is not None:
        candidatos = [e for e in candidatos if e.tipo == tipo]

    for espacio in candidatos:
        conflictos = []
        for actuacion in actuaciones:
            if actuacion.get("idEspacio") != espacio.id:
                continue
            if actuacion.get("estado") == "cancelada":
                continue
            try:
                inicio_actuacion = time.fromisoformat(actuacion["horaInicio"])
                fin_actuacion = time.fromisoformat(actuacion["horaFin"])
            except (KeyError, TypeError, ValueError):
                raise HTTPException(
                    status_code=503,
                    detail="Escaleta devolvió una actuación con datos no válidos"
                )
            if inicio_actuacion < horaFin and horaInicio < fin_actuacion:
                conflictos.append((inicio_actuacion, fin_actuacion))

        motivo = None
        if espacio.estado != "activo":
            motivo = f"El espacio está {espacio.estado}"
        elif conflictos:
            desde, hasta = conflictos[0]
            motivo = f"Existe una actuación programada de {desde.isoformat()} a {hasta.isoformat()}"

        resultado.append(DisponibilidadEspacio(
            idEspacio=espacio.id,
            nombreEspacio=espacio.nombre,
            fecha=fecha,
            horaInicio=horaInicio,
            horaFin=horaFin,
            disponible=not conflictos,
            motivo=motivo
        ))
    return resultado


# GET /api/espacios/tipo/{tipo}
@app.get("/api/espacios/tipo/{tipo}", response_model=list[Espacio])
def espacios_por_tipo(tipo: TipoEspacio):
    return persistencia.listar(Espacio, tipo=tipo)


# POST /api/espacios
@app.post("/api/espacios", response_model=Espacio, status_code=201, dependencies=[Depends(exigir_admin)])
def crear_espacio(datos: EspacioInput):
    if any(e.nombre.casefold() == datos.nombre.casefold() for e in persistencia.listar(Espacio)):
        raise HTTPException(status_code=409, detail="Ya existe un espacio con ese nombre")
    return persistencia.crear(datos, Espacio)


# GET /api/espacios/{idEspacio}
@app.get("/api/espacios/{idEspacio}", response_model=Espacio)
def obtener_espacio(idEspacio: int):
    return buscar_espacio(idEspacio)


# PUT /api/espacios/{idEspacio}
@app.put("/api/espacios/{idEspacio}", response_model=Espacio, dependencies=[Depends(exigir_admin)])
def modificar_espacio(idEspacio: int, datos: EspacioInput):
    espacio = buscar_espacio(idEspacio)
    if any(e.id != idEspacio and e.nombre.casefold() == datos.nombre.casefold() for e in persistencia.listar(Espacio)):
        raise HTTPException(status_code=409, detail="Ya existe un espacio con ese nombre")
    return persistencia.actualizar(idEspacio, datos, Espacio)


# DELETE /api/espacios/{idEspacio}
@app.delete("/api/espacios/{idEspacio}", status_code=204, dependencies=[Depends(exigir_admin)])
def eliminar_espacio(idEspacio: int):
    espacio = buscar_espacio(idEspacio)
    actuaciones = llamada_escaleta(f"/escaleta/espacio/{idEspacio}")
    if not isinstance(actuaciones, list):
        raise HTTPException(status_code=503, detail="Respuesta no válida de Escaleta")
    if actuaciones:
        raise HTTPException(
            status_code=409,
            detail="El espacio no se puede eliminar porque tiene actuaciones asociadas"
        )
    persistencia.eliminar(idEspacio)
    return None


# PATCH /api/espacios/{idEspacio}/estado
@app.patch("/api/espacios/{idEspacio}/estado", response_model=Espacio, dependencies=[Depends(exigir_admin)])
def actualizar_estado(idEspacio: int, datos: ActualizacionEstado):
    espacio = buscar_espacio(idEspacio)
    return persistencia.actualizar_campo(idEspacio, "estado", datos.estado, Espacio)


# PATCH /api/espacios/{idEspacio}/capacidad
@app.patch("/api/espacios/{idEspacio}/capacidad", response_model=Espacio, dependencies=[Depends(exigir_admin)])
def actualizar_capacidad(idEspacio: int, datos: ActualizacionCapacidad):
    espacio = buscar_espacio(idEspacio)
    return persistencia.actualizar_campo(idEspacio, "capacidad", datos.capacidad, Espacio)


# GET /api/espacios/{idEspacio}/actuaciones
@app.get(
    "/api/espacios/{idEspacio}/actuaciones",
    response_model=list[ActuacionEspacio]
)
def actuaciones_del_espacio(idEspacio: int):
    buscar_espacio(idEspacio)
    actuaciones = llamada_escaleta(f"/escaleta/espacio/{idEspacio}")
    if not isinstance(actuaciones, list):
        raise HTTPException(status_code=503, detail="Respuesta no válida de Escaleta")
    try:
        return [ActuacionEspacio.model_validate(a) for a in actuaciones]
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Escaleta devolvió actuaciones con datos no válidos"
        ) from exc
