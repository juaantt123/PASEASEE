from datetime import date, datetime, timezone
from typing import Literal
import hashlib
import hmac
import secrets
import sqlite3

from fastapi import FastAPI, Header, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from Usuarios.persistencia_usuarios import conectar, inicializar

app = FastAPI(title='API Usuarios - Subsonic Festival',
              description='Microservicio de gestion de usuarios', version='1.0.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['null'],
    allow_origin_regex=r'https?://(localhost|127\.0\.0\.1)(:\d+)?',
    allow_methods=['GET', 'POST', 'PATCH', 'PUT', 'DELETE'],
    allow_headers=['Content-Type', 'Authorization'],
)

TipoUsuario = Literal['cliente', 'proveedor', 'administrador']

class RegistroUsuario(BaseModel):
    nombre: str
    apellidos: str
    email: str
    password: str = Field(min_length=8)
    telefono: str | None = None
    fechaNacimiento: date | None = None
    tipo: Literal['cliente', 'proveedor']

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
    tipo: Literal['tarjeta', 'paypal']
    titular: str | None = None
    numero: str | None = None
    fechaCaducidad: str | None = None
    predeterminado: bool = False

class MetodoPago(BaseModel):
    id: int
    tipo: Literal['tarjeta', 'paypal']
    titular: str | None = None
    ultimosDigitos: str | None = None
    predeterminado: bool

class ActualizacionPerfil(BaseModel):
    nombre: str | None = None
    apellidos: str | None = None
    telefono: str | None = None
    fechaNacimiento: date | None = None

class FotoPerfil(BaseModel):
    url: str

class ActualizacionTipo(BaseModel):
    tipo: TipoUsuario

class MovimientoSaldo(BaseModel):
    importe: float = Field(gt=0, le=1000)
    concepto: str = Field(min_length=1, max_length=120)

class Login(BaseModel):
    email: str
    password: str

class Sesion(BaseModel):
    token: str
    tipo: str
    usuario: Usuario


def usuario_de_fila(fila):
    return Usuario(**{k: fila[k] for k in
                     ('id', 'nombre', 'apellidos', 'email', 'telefono',
                      'fechaNacimiento', 'tipo', 'fotoPerfil', 'fechaRegistro')})


def metodo_de_fila(fila):
    return MetodoPago(**{k: fila[k] for k in
                    ('id', 'tipo', 'titular', 'ultimosDigitos', 'predeterminado')})


def buscar_usuario(idUsuario: int):
    with conectar() as con:
        fila = con.execute('SELECT * FROM usuarios WHERE id=?', (idUsuario,)).fetchone()
    if fila is None:
        raise HTTPException(404, 'Usuario no encontrado')
    return usuario_de_fila(fila)


def buscar_usuario_email(email: str):
    with conectar() as con:
        fila = con.execute('SELECT * FROM usuarios WHERE email=?', (email,)).fetchone()
    return fila


def comprobar_email(email: str, excluir_id=None):
    with conectar() as con:
        existe = con.execute('SELECT 1 FROM usuarios WHERE email=? AND id!=?',
                             (email, excluir_id if excluir_id is not None else -1)).fetchone()
    if existe:
        raise HTTPException(409, 'El correo electronico ya esta registrado')


def generar_hash(password: str):
    salt = secrets.token_bytes(16)
    resultado = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 600000)
    return salt.hex(), resultado.hex()


def verificar_password(password: str, salt_hex: str, hash_hex: str):
    resultado = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt_hex), 600000)
    return hmac.compare_digest(resultado, bytes.fromhex(hash_hex))


def hash_token(token: str):
    return hashlib.sha256(token.encode()).hexdigest()


def usuario_de_sesion(authorization: str | None, id_usuario: int | None = None):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(401, 'Sesion no valida')
    token = authorization.removeprefix('Bearer ')
    with conectar() as con:
        fila = con.execute('SELECT idUsuario FROM sesiones WHERE token_hash=?',
                           (hash_token(token),)).fetchone()
    if fila is None or (id_usuario is not None and fila['idUsuario'] != id_usuario):
        raise HTTPException(401, 'Sesion no valida')
    return buscar_usuario(fila['idUsuario'])


def fecha_para_sql(fecha):
    return fecha.isoformat() if isinstance(fecha, (date, datetime)) else fecha


def centimos(importe: float):
    from decimal import Decimal, ROUND_HALF_UP
    return int((Decimal(str(importe)) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


@app.exception_handler(RequestValidationError)
async def error_validacion(request, exc):
    return JSONResponse(status_code=400, content={'codigo': 400, 'mensaje': 'Datos o parametros no validos'})

@app.exception_handler(HTTPException)
async def error_http(request, exc):
    return JSONResponse(status_code=exc.status_code,
                        content={'codigo': exc.status_code, 'mensaje': exc.detail})

@app.get('/')
def inicio():
    return {'mensaje': 'Microservicio Usuarios funcionando'}

@app.get('/api/usuarios', response_model=list[Usuario])
def listar_usuarios(tipo: TipoUsuario | None = None):
    with conectar() as con:
        if tipo is None:
            filas = con.execute('SELECT * FROM usuarios ORDER BY id').fetchall()
        else:
            filas = con.execute('SELECT * FROM usuarios WHERE tipo=? ORDER BY id', (tipo,)).fetchall()
    return [usuario_de_fila(fila) for fila in filas]

@app.post('/api/usuarios', response_model=Usuario, status_code=201)
def registrar_usuario(datos: RegistroUsuario):
    comprobar_email(datos.email)
    salt, hash_password = generar_hash(datos.password)
    with conectar() as con:
        try:
            cursor = con.execute('''
                INSERT INTO usuarios (nombre,apellidos,email,telefono,fechaNacimiento,
                                     tipo,fechaRegistro,salt,hash_password)
                VALUES (?,?,?,?,?,?,?,?,?)''',
                (datos.nombre, datos.apellidos, datos.email, datos.telefono,
                 fecha_para_sql(datos.fechaNacimiento), datos.tipo,
                 datetime.now(timezone.utc).isoformat(), salt, hash_password))
        except sqlite3.IntegrityError:
            raise HTTPException(409, 'El correo electronico ya esta registrado')
        nuevo_id = cursor.lastrowid
    return buscar_usuario(nuevo_id)

@app.post('/api/usuarios/login', response_model=Sesion)
def iniciar_sesion(datos: Login):
    fila = buscar_usuario_email(datos.email)
    if fila is None or not fila['salt'] or not fila['hash_password']:
        raise HTTPException(401, 'Credenciales incorrectas')
    if not verificar_password(datos.password, fila['salt'], fila['hash_password']):
        raise HTTPException(401, 'Credenciales incorrectas')
    token = secrets.token_urlsafe(32)
    with conectar() as con:
        con.execute('INSERT INTO sesiones (token_hash,idUsuario) VALUES (?,?)',
                    (hash_token(token), fila['id']))
    return Sesion(token=token, tipo='Bearer', usuario=buscar_usuario(fila['id']))

@app.get('/api/usuarios/sesion', response_model=Usuario)
def consultar_sesion(authorization: str | None = Header(default=None)):
    return usuario_de_sesion(authorization)

@app.get('/api/usuarios/{idUsuario}/saldo')
def consultar_saldo(idUsuario: int, authorization: str | None = Header(default=None)):
    usuario_de_sesion(authorization, idUsuario)
    with conectar() as con:
        fila = con.execute('SELECT saldo_centimos FROM usuarios WHERE id=?', (idUsuario,)).fetchone()
    return {'saldo': fila['saldo_centimos'] / 100}

@app.post('/api/usuarios/{idUsuario}/saldo/recargar')
def recargar_saldo(idUsuario: int, datos: MovimientoSaldo,
                  authorization: str | None = Header(default=None)):
    usuario_de_sesion(authorization, idUsuario)
    with conectar() as con:
        con.execute('UPDATE usuarios SET saldo_centimos=saldo_centimos+? WHERE id=?',
                    (centimos(datos.importe), idUsuario))
        saldo = con.execute('SELECT saldo_centimos FROM usuarios WHERE id=?', (idUsuario,)).fetchone()[0]
    return {'saldo': saldo / 100}

@app.post('/api/usuarios/{idUsuario}/saldo/gastar')
def gastar_saldo(idUsuario: int, datos: MovimientoSaldo,
                 authorization: str | None = Header(default=None)):
    usuario_de_sesion(authorization, idUsuario)
    with conectar() as con:
        cursor = con.execute('''UPDATE usuarios SET saldo_centimos=saldo_centimos-?
                                WHERE id=? AND saldo_centimos>=?''',
                             (centimos(datos.importe), idUsuario, centimos(datos.importe)))
        if cursor.rowcount == 0:
            raise HTTPException(409, 'Saldo de prueba insuficiente')
        saldo = con.execute('SELECT saldo_centimos FROM usuarios WHERE id=?', (idUsuario,)).fetchone()[0]
    return {'saldo': saldo / 100}

@app.get('/api/usuarios/{idUsuario}', response_model=Usuario)
def obtener_usuario(idUsuario: int):
    return buscar_usuario(idUsuario)

@app.put('/api/usuarios/{idUsuario}', response_model=Usuario)
def modificar_usuario(idUsuario: int, datos: UsuarioInput):
    buscar_usuario(idUsuario)
    comprobar_email(datos.email, excluir_id=idUsuario)
    with conectar() as con:
        try:
            con.execute('''UPDATE usuarios SET nombre=?,apellidos=?,email=?,telefono=?,
                           fechaNacimiento=? WHERE id=?''',
                        (datos.nombre, datos.apellidos, datos.email, datos.telefono,
                         fecha_para_sql(datos.fechaNacimiento), idUsuario))
        except sqlite3.IntegrityError:
            raise HTTPException(409, 'El correo electronico ya esta registrado')
    return buscar_usuario(idUsuario)

@app.delete('/api/usuarios/{idUsuario}', status_code=204)
def eliminar_usuario(idUsuario: int):
    buscar_usuario(idUsuario)
    with conectar() as con:
        con.execute('DELETE FROM usuarios WHERE id=?', (idUsuario,))
    return None

@app.get('/api/usuarios/{idUsuario}/metodos-pago', response_model=list[MetodoPago])
def obtener_metodos_pago(idUsuario: int):
    buscar_usuario(idUsuario)
    with conectar() as con:
        filas = con.execute('SELECT * FROM metodos_pago WHERE idUsuario=? ORDER BY id', (idUsuario,)).fetchall()
    return [metodo_de_fila(fila) for fila in filas]

@app.post('/api/usuarios/{idUsuario}/metodos-pago', response_model=MetodoPago, status_code=201)
def agregar_metodo_pago(idUsuario: int, datos: MetodoPagoInput):
    buscar_usuario(idUsuario)
    if datos.tipo == 'tarjeta':
        if not datos.numero or not (datos.numero.isdigit() and 12 <= len(datos.numero) <= 19):
            raise HTTPException(400, 'Numero de tarjeta no valido')
        if not datos.fechaCaducidad:
            raise HTTPException(400, 'Falta la fecha de caducidad')
        partes = datos.fechaCaducidad.split('/')
        if (len(partes) != 2 or len(partes[0]) != 2 or len(partes[1]) != 2
                or not all(p.isdigit() for p in partes) or not 1 <= int(partes[0]) <= 12):
            raise HTTPException(400, 'Fecha de caducidad no valida')
    with conectar() as con:
        hay_previos = con.execute('SELECT 1 FROM metodos_pago WHERE idUsuario=? LIMIT 1',
                                  (idUsuario,)).fetchone()
        predeterminado = bool(datos.predeterminado or not hay_previos)
        if predeterminado:
            con.execute('UPDATE metodos_pago SET predeterminado=0 WHERE idUsuario=?', (idUsuario,))
        cursor = con.execute('''
            INSERT INTO metodos_pago(idUsuario,tipo,titular,ultimosDigitos,predeterminado)
            VALUES (?,?,?,?,?)''',
            (idUsuario, datos.tipo, datos.titular,
             datos.numero[-4:] if datos.tipo == 'tarjeta' else None, int(predeterminado)))
        fila = con.execute('SELECT * FROM metodos_pago WHERE id=?', (cursor.lastrowid,)).fetchone()
    return metodo_de_fila(fila)

@app.delete('/api/usuarios/{idUsuario}/metodos-pago/{idMetodoPago}', status_code=204)
def eliminar_metodo_pago(idUsuario: int, idMetodoPago: int):
    buscar_usuario(idUsuario)
    with conectar() as con:
        fila = con.execute('SELECT * FROM metodos_pago WHERE id=? AND idUsuario=?',
                           (idMetodoPago, idUsuario)).fetchone()
        if fila is None:
            raise HTTPException(404, 'Metodo de pago no encontrado')
        con.execute('DELETE FROM metodos_pago WHERE id=?', (idMetodoPago,))
        if fila['predeterminado']:
            siguiente = con.execute('SELECT id FROM metodos_pago WHERE idUsuario=? ORDER BY id LIMIT 1',
                                    (idUsuario,)).fetchone()
            if siguiente:
                con.execute('UPDATE metodos_pago SET predeterminado=1 WHERE id=?', (siguiente['id'],))
    return None

@app.patch('/api/usuarios/{idUsuario}/perfil', response_model=Usuario)
def actualizar_perfil(idUsuario: int, datos: ActualizacionPerfil,
                      authorization: str | None = Header(default=None)):
    usuario_de_sesion(authorization, idUsuario)
    cambios = datos.model_dump(exclude_unset=True)
    if cambios:
        columnas = ', '.join(f'{campo}=?' for campo in cambios)
        valores = [fecha_para_sql(valor) for valor in cambios.values()]
        with conectar() as con:
            con.execute(f'UPDATE usuarios SET {columnas} WHERE id=?', (*valores, idUsuario))
    return buscar_usuario(idUsuario)

@app.put('/api/usuarios/{idUsuario}/foto', response_model=Usuario)
def actualizar_foto(idUsuario: int, datos: FotoPerfil):
    buscar_usuario(idUsuario)
    with conectar() as con:
        con.execute('UPDATE usuarios SET fotoPerfil=? WHERE id=?', (datos.url, idUsuario))
    return buscar_usuario(idUsuario)

@app.patch('/api/usuarios/{idUsuario}/tipo', response_model=Usuario)
def modificar_tipo_usuario(idUsuario: int, datos: ActualizacionTipo):
    buscar_usuario(idUsuario)
    with conectar() as con:
        con.execute('UPDATE usuarios SET tipo=? WHERE id=?', (datos.tipo, idUsuario))
    return buscar_usuario(idUsuario)

inicializar()
