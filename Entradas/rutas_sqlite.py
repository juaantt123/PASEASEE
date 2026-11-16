from datetime import datetime, timezone
from fastapi import Header, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import httpx
import hmac
import os
try:
    from .persistencia import conexion, inicializar
except ImportError:
    from persistencia import conexion, inicializar


def configurar(app, modelos, consultar_usuarios, url_usuarios):
    TipoEntrada, TipoEntradaInput, CompraEntrada, CompraEntradaInput, EntradaUsuario, ValidacionEntrada, EstadoEntrada, TipoNombre, EstadoTipo = modelos

    @app.on_event("startup")
    def inicio_bd():
        inicializar()

    @app.exception_handler(RequestValidationError)
    async def error_validacion(request, exc):
        return JSONResponse(status_code=400, content={"codigo": 400, "mensaje": "Datos o parametros no validos"})

    @app.exception_handler(HTTPException)
    async def error_http(request, exc):
        return JSONResponse(status_code=exc.status_code, content={"codigo": exc.status_code, "mensaje": str(exc.detail)})

    def buscar(con, tabla, campo, valor, mensaje):
        fila = con.execute(f"SELECT * FROM {tabla} WHERE {campo} = ?", (valor,)).fetchone()
        if fila is None:
            raise HTTPException(404, mensaje)
        return dict(fila)

    def tipo(con, id):
        return buscar(con, "tipos", "id", id, "Tipo de entrada no encontrado")

    def entrada(con, id):
        return buscar(con, "entradas", "idEntrada", id, "Entrada no encontrada")

    @app.get("/")
    def inicio():
        return {"mensaje": "Microservicio Entradas funcionando"}

    @app.get("/api/entradas", response_model=list[TipoEntrada])
    def listar_entradas(tipo: TipoNombre | None = None, estado: EstadoTipo | None = None):
        with conexion() as con:
            return [dict(f) for f in con.execute("SELECT * FROM tipos WHERE (? IS NULL OR nombre=?) AND (? IS NULL OR estado=?) ORDER BY id", (tipo, tipo, estado, estado))]

    @app.post("/api/entradas", response_model=TipoEntrada, status_code=201)
    def crear_tipo(datos: TipoEntradaInput):
        with conexion(True) as con:
            if con.execute("SELECT 1 FROM tipos WHERE nombre=?", (datos.nombre,)).fetchone():
                raise HTTPException(409, "Ya existe ese tipo de entrada")
            cur = con.execute("INSERT INTO tipos(nombre,descripcion,precio,stockTotal,stockDisponible,fechaInicioValidez,fechaFinValidez,estado) VALUES (?,?,?,?,?,?,?,?)", (datos.nombre, datos.descripcion, datos.precio, datos.stockTotal, datos.stockTotal, datos.fechaInicioValidez.isoformat(), datos.fechaFinValidez.isoformat(), 'disponible'))
            return tipo(con, cur.lastrowid)

    @app.get("/api/entradas/disponibles", response_model=list[TipoEntrada])
    def disponibles():
        with conexion() as con:
            return [dict(f) for f in con.execute("SELECT * FROM tipos WHERE stockDisponible > 0 ORDER BY id")]

    @app.get("/api/entradas/tipo/{nombre_tipo}", response_model=TipoEntrada)
    def por_tipo(nombre_tipo: TipoNombre):
        with conexion() as con:
            return buscar(con, "tipos", "nombre", nombre_tipo, "Tipo de entrada no encontrado")

    @app.get('/api/entradas/compras/resumen', tags=['Estadísticas'])
    def resumen_compras(x_clave_interna: str | None = Header(default=None)):
        clave = os.getenv('CLAVE_INTERNA_ESTADISTICAS', '')
        if not clave:
            raise HTTPException(503, 'Clave interna de estadisticas no configurada')
        if not x_clave_interna or not hmac.compare_digest(x_clave_interna, clave):
            raise HTTPException(403, 'Acceso interno no autorizado')
        with conexion() as con:
            filas = con.execute("""
                SELECT c.idCompra, c.tipoEntrada, c.cantidad, c.precioTotal, c.fechaCompra,
                       SUM(CASE WHEN e.estado != 'cancelada' THEN 1 ELSE 0 END) AS cantidadActiva
                FROM compras c JOIN entradas e ON e.idCompra = c.idCompra
                GROUP BY c.idCompra ORDER BY c.idCompra
            """).fetchall()
            return [dict(fila) for fila in filas]

    @app.post("/api/entradas/comprar", response_model=CompraEntrada, status_code=201)
    def comprar(datos: CompraEntradaInput):
        consultar_usuarios(datos.idUsuario, datos.idMetodoPago)
        with conexion(True) as con:
            t = tipo(con, datos.idTipoEntrada)
            if t['stockDisponible'] < datos.cantidad:
                raise HTTPException(409, "No hay suficientes entradas disponibles")
            ahora = datetime.now(timezone.utc).isoformat()
            cur = con.execute("INSERT INTO compras(idUsuario,idTipoEntrada,tipoEntrada,cantidad,precioTotal,fechaCompra,estado) VALUES (?,?,?,?,?,?,?)", (datos.idUsuario, t['id'], t['nombre'], datos.cantidad, round(t['precio']*datos.cantidad, 2), ahora, 'completada'))
            compra_id = cur.lastrowid
            for _ in range(datos.cantidad):
                cur = con.execute("INSERT INTO entradas(idCompra,idUsuario,idTipoEntrada,tipoEntrada,fechaCompra,fechaInicioValidez,fechaFinValidez,estado) VALUES (?,?,?,?,?,?,?,?)", (compra_id, datos.idUsuario, t['id'], t['nombre'], ahora, t['fechaInicioValidez'], t['fechaFinValidez'], 'valida'))
                con.execute("UPDATE entradas SET codigo=? WHERE idEntrada=?", (f"SUB-2027-{cur.lastrowid:06d}", cur.lastrowid))
            con.execute("UPDATE tipos SET stockDisponible=stockDisponible-?, estado=CASE WHEN stockDisponible-?=0 THEN 'agotada' ELSE 'disponible' END WHERE id=?", (datos.cantidad, datos.cantidad, t['id']))
            return buscar(con, 'compras', 'idCompra', compra_id, 'Compra no encontrada')

    @app.get("/api/entradas/usuarios/{idUsuario}", response_model=list[EntradaUsuario])
    def entradas_usuario(idUsuario: int, authorization: str | None = Header(default=None)):
        if not authorization or not authorization.startswith('Bearer '):
            raise HTTPException(401, 'Sesion no valida')
        try:
            sesion = httpx.get(f"{url_usuarios}/usuarios/sesion", headers={'Authorization': authorization}, timeout=5)
        except httpx.RequestError:
            raise HTTPException(503, 'Microservicio Usuarios no disponible')
        if sesion.status_code != 200:
            raise HTTPException(401, 'Sesion no valida')
        if sesion.json().get('id') != idUsuario:
            raise HTTPException(403, 'No puedes consultar las entradas de otro usuario')
        consultar_usuarios(idUsuario)
        with conexion() as con:
            return [dict(f) for f in con.execute('SELECT * FROM entradas WHERE idUsuario=? ORDER BY idEntrada', (idUsuario,))]

    @app.get('/api/entradas/compras/{idCompra}', response_model=CompraEntrada)
    def obtener_compra(idCompra: int):
        with conexion() as con:
            return buscar(con, 'compras', 'idCompra', idCompra, 'Compra no encontrada')

    @app.patch('/api/entradas/{idEntrada}/cancelar', response_model=EntradaUsuario)
    def cancelar(idEntrada: int):
        with conexion(True) as con:
            e = entrada(con, idEntrada)
            if e['estado'] != 'valida':
                raise HTTPException(409, 'La entrada no se puede cancelar')
            con.execute("UPDATE entradas SET estado='cancelada' WHERE idEntrada=?", (idEntrada,))
            con.execute("UPDATE tipos SET stockDisponible=stockDisponible+1, estado='disponible' WHERE id=?", (e['idTipoEntrada'],))
            if not con.execute("SELECT 1 FROM entradas WHERE idCompra=? AND estado!='cancelada' LIMIT 1", (e['idCompra'],)).fetchone():
                con.execute("UPDATE compras SET estado='cancelada' WHERE idCompra=?", (e['idCompra'],))
            return entrada(con, idEntrada)

    @app.post('/api/entradas/{idEntrada}/validar', response_model=ValidacionEntrada)
    def validar(idEntrada: int):
        with conexion(True) as con:
            if entrada(con, idEntrada)['estado'] != 'valida':
                raise HTTPException(409, 'Entrada cancelada o ya utilizada')
            con.execute("UPDATE entradas SET estado='utilizada' WHERE idEntrada=?", (idEntrada,))
            return ValidacionEntrada(idEntrada=idEntrada, valida=True, fechaValidacion=datetime.now(timezone.utc), mensaje='Entrada valida. Acceso permitido.')

    @app.get('/api/entradas/{idEntrada}/estado', response_model=EstadoEntrada)
    def estado_entrada(idEntrada: int):
        with conexion() as con:
            return entrada(con, idEntrada)

    @app.get('/api/entradas/{idTipoEntrada}', response_model=TipoEntrada)
    def obtener_tipo(idTipoEntrada: int):
        with conexion() as con:
            return tipo(con, idTipoEntrada)

    @app.put('/api/entradas/{idTipoEntrada}', response_model=TipoEntrada)
    def modificar(idTipoEntrada: int, datos: TipoEntradaInput):
        with conexion(True) as con:
            t = tipo(con, idTipoEntrada)
            if con.execute('SELECT 1 FROM tipos WHERE nombre=? AND id!=?', (datos.nombre, idTipoEntrada)).fetchone():
                raise HTTPException(409, 'Ya existe ese tipo de entrada')
            vendidas = t['stockTotal'] - t['stockDisponible']
            if datos.stockTotal < vendidas:
                raise HTTPException(400, 'El stock total no puede ser menor que las entradas vendidas')
            stock = datos.stockTotal - vendidas
            con.execute('UPDATE tipos SET nombre=?,descripcion=?,precio=?,stockTotal=?,stockDisponible=?,fechaInicioValidez=?,fechaFinValidez=?,estado=? WHERE id=?', (datos.nombre, datos.descripcion, datos.precio, datos.stockTotal, stock, datos.fechaInicioValidez.isoformat(), datos.fechaFinValidez.isoformat(), 'disponible' if stock else 'agotada', idTipoEntrada))
            return tipo(con, idTipoEntrada)

    @app.delete('/api/entradas/{idTipoEntrada}', status_code=204)
    def eliminar(idTipoEntrada: int):
        with conexion(True) as con:
            tipo(con, idTipoEntrada)
            if con.execute('SELECT 1 FROM compras WHERE idTipoEntrada=? LIMIT 1', (idTipoEntrada,)).fetchone():
                raise HTTPException(409, 'Existen compras asociadas')
            con.execute('DELETE FROM tipos WHERE id=?', (idTipoEntrada,))
