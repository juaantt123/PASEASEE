"""API y persistencia de Escaleta. Ejecutar desde la raíz del repositorio."""
from contextlib import asynccontextmanager, contextmanager
from datetime import date, datetime, time
from pathlib import Path
from typing import Annotated, Literal
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from zoneinfo import ZoneInfo
import json
import os
import sqlite3

from fastapi import FastAPI, HTTPException, Path as PathParam, Query, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field, ValidationError, computed_field, model_validator

DB_PATH = Path(os.getenv('ESCALETA_DB', str(Path(__file__).parent / 'data' / 'escaleta.sqlite3')))
ESPACIOS_URL = os.getenv('ESPACIOS_URL', 'http://127.0.0.1:8001/api').rstrip('/')
ESPACIOS_TIMEOUT = float(os.getenv('ESPACIOS_TIMEOUT', '3'))
FESTIVAL_TZ = ZoneInfo(os.getenv('FESTIVAL_TZ', 'Europe/Madrid'))
Id = Annotated[int, PathParam(ge=1)]
Estado = Literal['programada', 'en_curso', 'finalizada', 'cancelada']


class Horario(BaseModel):
    fecha: date
    horaInicio: time
    horaFin: time

    @model_validator(mode='after')
    def validar_horas(self):
        if self.horaInicio.tzinfo is not None or self.horaFin.tzinfo is not None:
            raise ValueError('Usa horas locales sin zona horaria')
        if self.horaFin <= self.horaInicio:
            raise ValueError('La hora final debe ser posterior a la inicial dentro del mismo día')
        return self


class ActuacionInput(Horario):
    idArtista: int = Field(ge=1)
    idEspacio: int = Field(ge=1)
    estado: Estado = 'programada'


class Actuacion(ActuacionInput):
    id: int
    nombreArtista: str
    nombreEspacio: str

    @computed_field
    @property
    def idActuacion(self) -> int:
        # Espacios.ActuacionEspacio necesita esta clave; id se mantiene para el YAML.
        return self.id


class ActualizacionEspacio(BaseModel):
    idEspacio: int = Field(ge=1)


class ArtistaInput(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    genero: str = Field(default='sin especificar', min_length=1, max_length=100)

    @model_validator(mode='after')
    def limpiar(self):
        self.nombre = self.nombre.strip()
        self.genero = self.genero.strip()
        if not self.nombre or not self.genero:
            raise ValueError('El nombre y el género no pueden estar vacíos')
        return self


class Artista(ArtistaInput):
    id: int


class EspacioRemoto(BaseModel):
    id: int
    nombre: str
    tipo: str
    estado: str


class Conflicto(BaseModel):
    idActuacion1: int
    idActuacion2: int
    idEspacio: int
    descripcion: str


class Error(BaseModel):
    codigo: int
    mensaje: str


@contextmanager
def conexion(escritura=False):
    con = sqlite3.connect(str(DB_PATH), timeout=10, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    try:
        if escritura:
            # Serializa comprobación de solapamientos y escritura, incluso con varias peticiones.
            con.execute('BEGIN IMMEDIATE')
        yield con
        if escritura:
            con.commit()
    except Exception:
        if escritura:
            con.rollback()
        raise
    finally:
        con.close()


def inicializar_bd():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with conexion() as con:
        con.execute('PRAGMA journal_mode=WAL')
        con.executescript('''
            CREATE TABLE IF NOT EXISTS artistas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                genero TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS actuaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                idArtista INTEGER NOT NULL REFERENCES artistas(id),
                idEspacio INTEGER NOT NULL,
                nombreEspacio TEXT NOT NULL,
                fecha TEXT NOT NULL,
                horaInicio TEXT NOT NULL,
                horaFin TEXT NOT NULL,
                estado TEXT NOT NULL CHECK(estado IN ('programada','en_curso','finalizada','cancelada'))
            );
            CREATE INDEX IF NOT EXISTS idx_espacio_fecha ON actuaciones(idEspacio, fecha);
        ''')
        # Se añade una sola vez; el indicador evita reaparecer si el usuario lo elimina.
        con.execute('CREATE TABLE IF NOT EXISTS metadatos (clave TEXT PRIMARY KEY)')
        with_seed = con.execute("SELECT 1 FROM metadatos WHERE clave='semilla_v1'").fetchone()
    if not with_seed:
        with conexion(True) as con:
            if not con.execute("SELECT 1 FROM metadatos WHERE clave='semilla_v1'").fetchone():
                con.execute("INSERT OR IGNORE INTO artistas(id,nombre,genero) VALUES(8,'Arde Bogotá','rock')")
                con.execute("INSERT INTO metadatos(clave) VALUES('semilla_v1')")


@asynccontextmanager
async def lifespan(app):
    inicializar_bd()
    yield


app = FastAPI(title='API Escaleta - Subsonic Festival', version='1.0.0', lifespan=lifespan,
              responses={code: {'model': Error, 'description': text} for code,text in {
                  400: 'Datos o parámetros no válidos.', 404: 'Recurso no encontrado.',
                  409: 'Conflicto de horario, recurso no operativo o dependencia existente.',
                  503: 'Espacios o la base de datos de Escaleta no están disponibles.'}.items()})


@app.exception_handler(RequestValidationError)
async def error_validacion(request, exc):
    return JSONResponse(status_code=400, content={'codigo': 400, 'mensaje': 'Datos o parámetros no válidos. Comprueba identificadores, fecha y horas.'})


@app.exception_handler(HTTPException)
async def error_http(request, exc):
    return JSONResponse(status_code=exc.status_code, content={'codigo': exc.status_code, 'mensaje': exc.detail})


@app.exception_handler(sqlite3.OperationalError)
async def error_bd(request, exc):
    return JSONResponse(status_code=503, content={'codigo': 503, 'mensaje': 'No se puede acceder a la base de datos de Escaleta.'})


def consultar_espacio(identificador):
    try:
        with urlopen(f'{ESPACIOS_URL}/espacios/{identificador}', timeout=ESPACIOS_TIMEOUT) as r:
            espacio = EspacioRemoto.model_validate(json.loads(r.read().decode('utf-8')))
    except HTTPError as exc:
        if exc.code == 404:
            raise HTTPException(404, 'El espacio indicado no existe') from exc
        raise HTTPException(503, 'Espacios no está disponible o ha rechazado la consulta') from exc
    except (URLError, OSError, TimeoutError, ValueError, ValidationError) as exc:
        raise HTTPException(503, 'No se puede consultar Espacios o su respuesta no es válida') from exc
    if espacio.id != identificador:
        raise HTTPException(503, 'Espacios ha devuelto un identificador incorrecto')
    if espacio.tipo != 'escenario' or espacio.estado != 'activo':
        raise HTTPException(409, 'El espacio debe ser un escenario activo')
    return espacio


SELECT_ACTUACIONES = '''SELECT a.*, ar.nombre AS nombreArtista FROM actuaciones a
                       JOIN artistas ar ON ar.id=a.idArtista'''


def buscar_actuacion(con, identificador):
    fila = con.execute(SELECT_ACTUACIONES+' WHERE a.id=?', (identificador,)).fetchone()
    if fila is None:
        raise HTTPException(404, 'Actuación no encontrada')
    return Actuacion.model_validate(dict(fila))


def buscar_artista(con, identificador):
    fila = con.execute('SELECT * FROM artistas WHERE id=?', (identificador,)).fetchone()
    if fila is None:
        raise HTTPException(404, 'Artista no encontrado')
    return Artista.model_validate(dict(fila))


def validar_actuacion(con, datos, excluir=0):
    buscar_artista(con, datos.idArtista)
    espacio = consultar_espacio(datos.idEspacio)
    if datos.estado != 'cancelada':
        conflicto = con.execute('''SELECT id FROM actuaciones WHERE id<>? AND fecha=?
            AND estado<>'cancelada' AND (idEspacio=? OR idArtista=?)
            AND horaInicio < ? AND horaFin > ? LIMIT 1''',
            (excluir, datos.fecha.isoformat(), datos.idEspacio, datos.idArtista,
             datos.horaFin.isoformat(), datos.horaInicio.isoformat())).fetchone()
        if conflicto:
            raise HTTPException(409, 'El escenario o el artista ya tiene una actuación en esa franja')
    return espacio


@app.get('/')
def inicio():
    return {'mensaje': 'Microservicio Escaleta funcionando'}


@app.get('/api/escaleta', response_model=list[Actuacion], tags=['Escaleta'])
def listar_actuaciones(fecha: date | None = None,
                       idEspacio: Annotated[int | None, Query(ge=1)] = None,
                       idArtista: Annotated[int | None, Query(ge=1)] = None):
    filtros, valores = [], []
    for campo, valor in [('fecha', fecha.isoformat() if fecha else None), ('idEspacio', idEspacio), ('idArtista', idArtista)]:
        if valor is not None:
            filtros.append('a.'+campo+'=?')
            valores.append(valor)
    sql = SELECT_ACTUACIONES+(' WHERE '+' AND '.join(filtros) if filtros else '')+' ORDER BY a.fecha,a.horaInicio,a.id'
    with conexion() as con:
        return [dict(fila) for fila in con.execute(sql, valores)]


# Rutas fijas antes de /{idActuacion}, para que no se interpreten como identificadores.
@app.get('/api/escaleta/proximas', response_model=list[Actuacion], tags=['Escaleta'])
def proximas():
    ahora = datetime.now(FESTIVAL_TZ)
    return [a for a in listar_actuaciones() if a['estado'] == 'programada'
            and datetime.combine(date.fromisoformat(a['fecha']), time.fromisoformat(a['horaInicio']), FESTIVAL_TZ) >= ahora]


@app.get('/api/escaleta/conflictos', response_model=list[Conflicto], tags=['Escaleta'])
def conflictos():
    with conexion() as con:
        filas = con.execute('''SELECT a.id AS idActuacion1,b.id AS idActuacion2,a.idEspacio,
            'Actuaciones con espacio o artista coincidente en horario incompatible' AS descripcion
            FROM actuaciones a JOIN actuaciones b ON a.id<b.id AND a.fecha=b.fecha
            AND (a.idEspacio=b.idEspacio OR a.idArtista=b.idArtista)
            AND a.horaInicio<b.horaFin AND b.horaInicio<a.horaFin
            WHERE a.estado<>'cancelada' AND b.estado<>'cancelada'
            ORDER BY a.id,b.id''').fetchall()
        return [dict(fila) for fila in filas]


@app.get('/api/escaleta/dia/{fecha}', response_model=list[Actuacion], tags=['Escaleta'])
def por_dia(fecha: date):
    return listar_actuaciones(fecha=fecha)


@app.get('/api/escaleta/espacio/{idEspacio}', response_model=list[Actuacion], tags=['Escaleta'])
def por_espacio(idEspacio: Id):
    # No llama a Espacios: este endpoint lo utiliza Espacios para su disponibilidad.
    return listar_actuaciones(idEspacio=idEspacio)


@app.get('/api/escaleta/artista/{idArtista}', response_model=list[Actuacion], tags=['Escaleta'])
def por_artista(idArtista: Id):
    with conexion() as con:
        buscar_artista(con, idArtista)
    return listar_actuaciones(idArtista=idArtista)


@app.get('/api/escaleta/artistas', response_model=list[Artista], tags=['Artistas'])
def listar_artistas():
    with conexion() as con:
        return [dict(fila) for fila in con.execute('SELECT * FROM artistas ORDER BY id')]


def nombre_artista_unico(con, nombre, excluir=0):
    if any(r['id'] != excluir and r['nombre'].casefold()==nombre.casefold()
           for r in con.execute('SELECT id,nombre FROM artistas')):
        raise HTTPException(409, 'Ya existe un artista con ese nombre')


@app.post('/api/escaleta/artistas', response_model=Artista, status_code=201, tags=['Artistas'])
def crear_artista(datos: ArtistaInput):
    with conexion(True) as con:
        nombre_artista_unico(con, datos.nombre)
        cur = con.execute('INSERT INTO artistas(nombre,genero) VALUES(?,?)', (datos.nombre, datos.genero))
        return buscar_artista(con, cur.lastrowid)


@app.get('/api/escaleta/artistas/{idArtista}', response_model=Artista, tags=['Artistas'])
def obtener_artista(idArtista: Id):
    with conexion() as con:
        return buscar_artista(con, idArtista)


@app.put('/api/escaleta/artistas/{idArtista}', response_model=Artista, tags=['Artistas'])
def modificar_artista(idArtista: Id, datos: ArtistaInput):
    with conexion(True) as con:
        buscar_artista(con, idArtista)
        nombre_artista_unico(con, datos.nombre, idArtista)
        con.execute('UPDATE artistas SET nombre=?,genero=? WHERE id=?', (datos.nombre, datos.genero, idArtista))
        return buscar_artista(con, idArtista)


@app.delete('/api/escaleta/artistas/{idArtista}', status_code=204, tags=['Artistas'])
def eliminar_artista(idArtista: Id):
    with conexion(True) as con:
        buscar_artista(con, idArtista)
        if con.execute('SELECT 1 FROM actuaciones WHERE idArtista=? LIMIT 1', (idArtista,)).fetchone():
            raise HTTPException(409, 'El artista tiene actuaciones asociadas')
        con.execute('DELETE FROM artistas WHERE id=?', (idArtista,))
    return Response(status_code=204)


@app.post('/api/escaleta', response_model=Actuacion, status_code=201, tags=['Escaleta'])
def crear_actuacion(datos: ActuacionInput):
    with conexion(True) as con:
        espacio = validar_actuacion(con, datos)
        cur = con.execute('''INSERT INTO actuaciones(idArtista,idEspacio,nombreEspacio,fecha,horaInicio,horaFin,estado)
            VALUES(?,?,?,?,?,?,?)''', (datos.idArtista, datos.idEspacio, espacio.nombre,
            datos.fecha.isoformat(), datos.horaInicio.isoformat(), datos.horaFin.isoformat(), datos.estado))
        return buscar_actuacion(con, cur.lastrowid)


@app.get('/api/escaleta/{idActuacion}', response_model=Actuacion, tags=['Escaleta'])
def obtener_actuacion(idActuacion: Id):
    with conexion() as con:
        return buscar_actuacion(con, idActuacion)


def guardar_actuacion(con, identificador, datos):
    espacio = validar_actuacion(con, datos, identificador)
    con.execute('''UPDATE actuaciones SET idArtista=?,idEspacio=?,nombreEspacio=?,fecha=?,
        horaInicio=?,horaFin=?,estado=? WHERE id=?''', (datos.idArtista, datos.idEspacio, espacio.nombre,
        datos.fecha.isoformat(), datos.horaInicio.isoformat(), datos.horaFin.isoformat(), datos.estado, identificador))
    return buscar_actuacion(con, identificador)


@app.put('/api/escaleta/{idActuacion}', response_model=Actuacion, tags=['Escaleta'])
def modificar_actuacion(idActuacion: Id, datos: ActuacionInput):
    with conexion(True) as con:
        buscar_actuacion(con, idActuacion)
        return guardar_actuacion(con, idActuacion, datos)


@app.patch('/api/escaleta/{idActuacion}/horario', response_model=Actuacion, tags=['Escaleta'])
def cambiar_horario(idActuacion: Id, datos: Horario):
    with conexion(True) as con:
        anterior = buscar_actuacion(con, idActuacion)
        entrada = ActuacionInput.model_validate({**anterior.model_dump(), **datos.model_dump()})
        return guardar_actuacion(con, idActuacion, entrada)


@app.patch('/api/escaleta/{idActuacion}/espacio', response_model=Actuacion, tags=['Escaleta'])
def cambiar_espacio(idActuacion: Id, datos: ActualizacionEspacio):
    with conexion(True) as con:
        anterior = buscar_actuacion(con, idActuacion)
        entrada = ActuacionInput.model_validate({**anterior.model_dump(), **datos.model_dump()})
        return guardar_actuacion(con, idActuacion, entrada)


@app.delete('/api/escaleta/{idActuacion}', status_code=204, tags=['Escaleta'])
def eliminar_actuacion(idActuacion: Id):
    with conexion(True) as con:
        buscar_actuacion(con, idActuacion)
        con.execute('DELETE FROM actuaciones WHERE id=?', (idActuacion,))
    return Response(status_code=204)


def esquema_openapi():
    if app.openapi_schema is None:
        esquema = get_openapi(title=app.title, version=app.version, routes=app.routes)
        # El manejador RequestValidationError devuelve 400, no el 422 automático.
        for item in esquema['paths'].values():
            for op in item.values():
                if isinstance(op, dict):
                    op.get('responses', {}).pop('422', None)
        app.openapi_schema = esquema
    return app.openapi_schema


app.openapi = esquema_openapi
