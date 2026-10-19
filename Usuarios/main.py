
from datetime import datetime, date, timezone
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


app = FastAPI(
    title="API Usuarios - Subsonic Festival",
    description="Microservicio de gestion de usuarios",
    version="1.0.0"
)


# ==========================================
# MODELOS DE DATOS
# ==========================================

TipoUsuario = Literal["cliente", "proveedor", "administrador"]


class RegistroUsuario(BaseModel):
    nombre: str
    apellidos: str
    email: str
    password: str
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
    comprobar_email(datos.email)

    nuevo_id = max(
        (usuario.id for usuario in usuarios),
        default=0
    ) + 1

    nuevo_usuario = Usuario(
        id=nuevo_id,
        **datos.model_dump(exclude={"password"}),
        fechaRegistro=datetime.now(timezone.utc)
    )

    usuarios.append(nuevo_usuario)

    return nuevo_usuario


# GET /api/usuarios/{idUsuario}
@app.get(
    "/api/usuarios/{idUsuario}",
    response_model=Usuario
)
def obtener_usuario(idUsuario: int):
    return buscar_usuario(idUsuario)


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


# DELETE /api/usuarios/{idUsuario}
@app.delete(
    "/api/usuarios/{idUsuario}",
    status_code=204
)
def eliminar_usuario(idUsuario: int):
    usuario = buscar_usuario(idUsuario)

    usuarios.remove(usuario)

    # Eliminar tambien sus metodos de pago
    metodos_pago.pop(idUsuario, None)

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
        idUsuario, []
    )

    # Validar numero de tarjeta de prueba
    if datos.tipo == "tarjeta":
        if not datos.numero or not (
            datos.numero.isdigit()
            and 12 <= len(datos.numero) <= 19
        ):
            raise HTTPException(
                status_code=400,
                detail="Numero de tarjeta no valido"
            )

    # Generar identificador
    todos = [
        metodo.id
        for metodos in metodos_pago.values()
        for metodo in metodos
    ]

    nuevo_id = max(todos, default=0) + 1

    # Configurar metodo predeterminado
    if datos.predeterminado or not lista:
        for metodo in lista:
            metodo.predeterminado = False

        es_predeterminado = True
    else:
        es_predeterminado = False

    # Crear metodo de pago
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

    lista.append(nuevo_metodo)

    return nuevo_metodo


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
