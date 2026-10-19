
from datetime import datetime, date, timezone
from typing import Literal
import hashlib
import hmac
import secrets

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


# ==========================================
# CONFIGURACION DE FASTAPI
# ==========================================

app = FastAPI(
    title="API Usuarios - Subsonic Festival",
    description="Microservicio de gestion de usuarios",
    version="1.0.0"
)


# ==========================================
# MODELOS DE DATOS
# ==========================================

TipoUsuario = Literal[
    "cliente",
    "proveedor",
    "administrador"
]


class RegistroUsuario(BaseModel):
    nombre: str
    apellidos: str
    email: str
    password: str = Field(min_length=8)
    telefono: str | None = None
    fechaNacimiento: date | None = None
    tipo: Literal["cliente", "proveedor"]


class UsuarioInput(BaseModel):
    nombre: str
    apellidos: str
    email: str
    telefono: str | None = None
    fechaNacimiento: date | None = None


class Usuario(BaseModel):
    id: int
    nombre: str
    apellidos: str
    email: str
    telefono: str | None = None
    fechaNacimiento: date | None = None
    tipo: TipoUsuario
    fotoPerfil: str | None = None
    fechaRegistro: datetime


# ==========================================
# MODELOS DE METODOS DE PAGO
# ==========================================

class MetodoPagoInput(BaseModel):
    tipo: Literal["tarjeta", "paypal"]
    titular: str | None = None
    numero: str | None = None
    fechaCaducidad: str | None = None
    predeterminado: bool = False


class MetodoPago(BaseModel):
    id: int
    tipo: Literal["tarjeta", "paypal"]
    titular: str | None = None
    ultimosDigitos: str | None = None
    predeterminado: bool


# ==========================================
# MODELOS DE ACTUALIZACION
# ==========================================

class ActualizacionPerfil(BaseModel):
    nombre: str | None = None
    apellidos: str | None = None
    telefono: str | None = None
    fechaNacimiento: date | None = None


class FotoPerfil(BaseModel):
    url: str


class ActualizacionTipo(BaseModel):
    tipo: TipoUsuario


# ==========================================
# MODELOS DEL LOGIN
# ==========================================

class Login(BaseModel):
    email: str
    password: str


class Sesion(BaseModel):
    token: str
    tipo: str
    usuario: Usuario


# ==========================================
# DATOS PROVISIONALES
# ==========================================

usuarios = [
    Usuario(
        id=25,
        nombre="Laura",
        apellidos="Garcia Sanchez",
        email="laura@email.com",
        tipo="cliente",
        fechaRegistro=datetime(
            2027, 4, 10, 12, 30,
            tzinfo=timezone.utc
        )
    )
]


# Metodos de pago iniciales para las pruebas
metodos_pago = {
    25: [
        MetodoPago(
            id=4,
            tipo="tarjeta",
            titular="Laura Garcia Sanchez",
            ultimosDigitos="4582",
            predeterminado=True
        )
    ]
}


# Contraseñas guardadas como hash
# El usuario inicial Laura no tiene contraseña
passwords = {}


# Sesiones provisionales en memoria
sesiones = {}


# ==========================================
# SEGURIDAD DE CONTRASEÑAS
# ==========================================

def generar_hash(password: str):
    salt = secrets.token_bytes(16)

    hash_password = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        600000
    )

    return {
        "salt": salt.hex(),
        "hash": hash_password.hex()
    }


def verificar_password(password: str, datos_hash: dict):
    salt = bytes.fromhex(datos_hash["salt"])

    hash_comprobacion = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        600000
    )

    return hmac.compare_digest(
        hash_comprobacion,
        bytes.fromhex(datos_hash["hash"])
    )


# ==========================================
# FUNCIONES AUXILIARES
# ==========================================

def buscar_usuario(idUsuario: int):
    for usuario in usuarios:
        if usuario.id == idUsuario:
            return usuario

    raise HTTPException(
        status_code=404,
        detail="Usuario no encontrado"
    )


def buscar_usuario_email(email: str):
    for usuario in usuarios:
        if usuario.email.lower() == email.lower():
            return usuario

    return None


def comprobar_email(email: str, excluir_id=None):
    for usuario in usuarios:
        if (
            usuario.email.lower() == email.lower()
            and usuario.id != excluir_id
        ):
            raise HTTPException(
                status_code=409,
                detail="El correo electronico ya esta registrado"
            )


# ==========================================
# VALIDACION DE ERRORES
# ==========================================

@app.exception_handler(RequestValidationError)
async def error_validacion(request, exc):
    return JSONResponse(
        status_code=400,
        content={
            "codigo": 400,
            "mensaje": "Datos o parametros no validos"
        }
    )


@app.exception_handler(HTTPException)
async def error_http(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "codigo": exc.status_code,
            "mensaje": exc.detail
        }
    )


# ==========================================
# COMPROBAR MICROSERVICIO
# ==========================================

@app.get("/")
def inicio():
    return {
        "mensaje": "Microservicio Usuarios funcionando"
    }


# ==========================================
# GESTION DE USUARIOS
# ==========================================

# GET /api/usuarios
@app.get(
    "/api/usuarios",
    response_model=list[Usuario]
)
def listar_usuarios(tipo: TipoUsuario | None = None):

    if tipo is not None:
        return [
            usuario for usuario in usuarios
            if usuario.tipo == tipo
        ]

    return usuarios


# POST /api/usuarios
@app.post(
    "/api/usuarios",
    response_model=Usuario,
    status_code=201
)
def registrar_usuario(datos: RegistroUsuario):

    # Comprobar que el correo no existe
    comprobar_email(datos.email)

    # Generar identificador
    nuevo_id = max(
        (usuario.id for usuario in usuarios),
        default=0
    ) + 1

    # Crear usuario sin incluir contraseña
    nuevo_usuario = Usuario(
        id=nuevo_id,
        **datos.model_dump(exclude={"password"}),
        fechaRegistro=datetime.now(timezone.utc)
    )

    # Guardar usuario
    usuarios.append(nuevo_usuario)

    # Guardar hash de la contraseña
    passwords[nuevo_id] = generar_hash(
        datos.password
    )

    return nuevo_usuario


# ==========================================
# INICIO DE SESION
# ==========================================

# POST /api/usuarios/login
@app.post(
    "/api/usuarios/login",
    response_model=Sesion
)
def iniciar_sesion(datos: Login):

    # Buscar el usuario por su correo
    usuario = buscar_usuario_email(datos.email)

    if usuario is None:
        raise HTTPException(
            status_code=401,
            detail="Credenciales incorrectas"
        )

    # Buscar contraseña guardada
    datos_hash = passwords.get(usuario.id)

    if datos_hash is None:
        raise HTTPException(
            status_code=401,
            detail="Credenciales incorrectas"
        )

    # Comprobar contraseña
    if not verificar_password(
        datos.password,
        datos_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Credenciales incorrectas"
        )

    # Generar token de sesion
    token = secrets.token_urlsafe(32)

    # Guardar sesion provisional
    sesiones[token] = usuario.id

    return Sesion(
        token=token,
        tipo="Bearer",
        usuario=usuario
    )


# ==========================================
# CONSULTAR USUARIO
# ==========================================

# GET /api/usuarios/{idUsuario}
@app.get(
    "/api/usuarios/{idUsuario}",
    response_model=Usuario
)
def obtener_usuario(idUsuario: int):

    return buscar_usuario(idUsuario)


# ==========================================
# MODIFICAR USUARIO
# ==========================================

# PUT /api/usuarios/{idUsuario}
@app.put(
    "/api/usuarios/{idUsuario}",
    response_model=Usuario
)
def modificar_usuario(
    idUsuario: int,
    datos: UsuarioInput
):

    usuario = buscar_usuario(idUsuario)

    comprobar_email(
        datos.email,
        excluir_id=idUsuario
    )

    for campo, valor in datos.model_dump().items():
        setattr(usuario, campo, valor)

    return usuario


# ==========================================
# ELIMINAR USUARIO
# ==========================================

# DELETE /api/usuarios/{idUsuario}
@app.delete(
    "/api/usuarios/{idUsuario}",
    status_code=204
)
def eliminar_usuario(idUsuario: int):

    usuario = buscar_usuario(idUsuario)

    # Eliminar usuario
    usuarios.remove(usuario)

    # Eliminar metodos de pago
    metodos_pago.pop(idUsuario, None)

    # Eliminar contraseña
    passwords.pop(idUsuario, None)

    # Eliminar sesiones del usuario
    for token, usuario_id in list(sesiones.items()):
        if usuario_id == idUsuario:
            sesiones.pop(token, None)

    return None


# ==========================================
# GESTION DE METODOS DE PAGO
# ==========================================

# GET /api/usuarios/{idUsuario}/metodos-pago
@app.get(
    "/api/usuarios/{idUsuario}/metodos-pago",
    response_model=list[MetodoPago]
)
def obtener_metodos_pago(idUsuario: int):

    buscar_usuario(idUsuario)

    return metodos_pago.get(idUsuario, [])


# ==========================================
# AÑADIR METODO DE PAGO
# ==========================================

# POST /api/usuarios/{idUsuario}/metodos-pago
@app.post(
    "/api/usuarios/{idUsuario}/metodos-pago",
    response_model=MetodoPago,
    status_code=201
)
def agregar_metodo_pago(
    idUsuario: int,
    datos: MetodoPagoInput
):

    buscar_usuario(idUsuario)

    lista = metodos_pago.setdefault(
        idUsuario,
        []
    )

    # Validar los datos de una tarjeta
    # Solo se utilizaran tarjetas ficticias
    if datos.tipo == "tarjeta":

        if not datos.numero or not (
            datos.numero.isdigit()
            and 12 <= len(datos.numero) <= 19
        ):
            raise HTTPException(
                status_code=400,
                detail="Numero de tarjeta no valido"
            )

        if not datos.fechaCaducidad:
            raise HTTPException(
                status_code=400,
                detail="Falta la fecha de caducidad"
            )

        partes = datos.fechaCaducidad.split("/")

        if (
            len(partes) != 2
            or len(partes[0]) != 2
            or len(partes[1]) != 2
            or not all(p.isdigit() for p in partes)
            or not 1 <= int(partes[0]) <= 12
        ):
            raise HTTPException(
                status_code=400,
                detail="Fecha de caducidad no valida"
            )

    # Calcular nuevo identificador
    todos = [
        metodo.id
        for metodos in metodos_pago.values()
        for metodo in metodos
    ]

    nuevo_id = max(
        todos,
        default=0
    ) + 1

    # Asignar metodo predeterminado
    if datos.predeterminado or not lista:

        for metodo in lista:
            metodo.predeterminado = False

        es_predeterminado = True

    else:
        es_predeterminado = False

    # Crear nuevo metodo
    nuevo_metodo = MetodoPago(
        id=nuevo_id,
        tipo=datos.tipo,
        titular=datos.titular,
        ultimosDigitos=(
            datos.numero[-4:]
            if datos.tipo == "tarjeta"
            else None
        ),
        predeterminado=es_predeterminado
    )

    # Guardar metodo de pago
    lista.append(nuevo_metodo)

    return nuevo_metodo


# ==========================================
# ELIMINAR METODO DE PAGO
# ==========================================

# DELETE /api/usuarios/{idUsuario}/metodos-pago/{idMetodoPago}
@app.delete(
    "/api/usuarios/{idUsuario}/metodos-pago/{idMetodoPago}",
    status_code=204
)
def eliminar_metodo_pago(
    idUsuario: int,
    idMetodoPago: int
):

    buscar_usuario(idUsuario)

    lista = metodos_pago.get(idUsuario, [])

    for metodo in lista:

        if metodo.id == idMetodoPago:

            era_predeterminado = metodo.predeterminado

            lista.remove(metodo)

            # Asignar otro metodo predeterminado
            if era_predeterminado and lista:
                lista[0].predeterminado = True

            return None

    raise HTTPException(
        status_code=404,
        detail="Metodo de pago no encontrado"
    )


# ==========================================
# ACTUALIZACION DE PERFIL
# ==========================================

# PATCH /api/usuarios/{idUsuario}/perfil
@app.patch(
    "/api/usuarios/{idUsuario}/perfil",
    response_model=Usuario
)
def actualizar_perfil(
    idUsuario: int,
    datos: ActualizacionPerfil
):

    usuario = buscar_usuario(idUsuario)

    for campo, valor in datos.model_dump(
        exclude_unset=True
    ).items():
        setattr(usuario, campo, valor)

    return usuario


# ==========================================
# ACTUALIZACION DE FOTO
# ==========================================

# PUT /api/usuarios/{idUsuario}/foto
@app.put(
    "/api/usuarios/{idUsuario}/foto",
    response_model=Usuario
)
def actualizar_foto(
    idUsuario: int,
    datos: FotoPerfil
):

    usuario = buscar_usuario(idUsuario)

    usuario.fotoPerfil = datos.url

    return usuario


# ==========================================
# MODIFICACION DEL TIPO DE USUARIO
# ==========================================

# PATCH /api/usuarios/{idUsuario}/tipo
@app.patch(
    "/api/usuarios/{idUsuario}/tipo",
    response_model=Usuario
)
def modificar_tipo_usuario(
    idUsuario: int,
    datos: ActualizacionTipo
):

    usuario = buscar_usuario(idUsuario)

    usuario.tipo = datos.tipo

    return usuario
