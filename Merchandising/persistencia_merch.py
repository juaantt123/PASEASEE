"""Persistencia SQLite del microservicio Merchandising."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import os
import sqlite3

from fastapi import HTTPException

# Categorías para las que es obligatorio indicar la talla al comprar
CATEGORIAS_CON_TALLA = ("camiseta", "sudadera")


def ruta_bd() -> Path:
    # Se lee en cada conexión para poder aislar la base de datos en las pruebas.
    return Path(os.getenv(
        "MERCHANDISING_DB",
        Path(__file__).parent / "data" / "merchandising.sqlite3"
    ))


@contextmanager
def conexion(escritura=False):
    ruta = ruta_bd()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(ruta, timeout=10, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        if escritura:
            # Serializa las escrituras: la comprobación del stock y su descuento
            # se hacen sin que otra petición pueda intercalarse.
            con.execute("BEGIN IMMEDIATE")
        yield con
        if escritura:
            con.commit()
    except Exception:
        if escritura:
            con.rollback()
        raise
    finally:
        con.close()


def inicializar():
    with conexion(True) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            categoria TEXT NOT NULL,
            precio REAL NOT NULL CHECK(precio >= 0),
            stock INTEGER NOT NULL CHECK(stock >= 0),
            imagen TEXT
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS compras (
            idCompra INTEGER PRIMARY KEY AUTOINCREMENT,
            idUsuario INTEGER NOT NULL,
            idProducto INTEGER NOT NULL REFERENCES productos(id),
            cantidad INTEGER NOT NULL CHECK(cantidad >= 1),
            talla TEXT,
            precioTotal REAL NOT NULL,
            fechaCompra TEXT NOT NULL,
            estado TEXT NOT NULL
        )""")
        columnas = {fila['name'] for fila in con.execute('PRAGMA table_info(productos)')}
        if 'idProveedor' not in columnas:
            con.execute('ALTER TABLE productos ADD COLUMN idProveedor INTEGER')
        con.execute("CREATE TABLE IF NOT EXISTS configuracion (clave TEXT PRIMARY KEY)")
        # Los productos iniciales se insertan una sola vez; si luego se borran
        # desde el panel, no vuelven a aparecer al reiniciar.
        if not con.execute("SELECT 1 FROM configuracion WHERE clave='inicializada'").fetchone():
            con.executemany(
                "INSERT INTO productos(id,nombre,descripcion,categoria,precio,stock,imagen) "
                "VALUES (?,?,?,?,?,?,?)", [
                    (1, "Camiseta oficial Subsonic 2027",
                     "Camiseta de algodón con el cartel de la edición.",
                     "camiseta", 25.0, 300, "camiseta_oficial.png"),
                    (2, "Sudadera Subsonic Night",
                     "Sudadera con capucha y logotipo reflectante.",
                     "sudadera", 45.0, 120, "sudadera_night.png"),
                    (3, "Póster conmemorativo",
                     "Póster numerado de la edición 2027.",
                     "poster", 12.0, 0, "poster_2027.png"),
                ])
            con.execute("INSERT INTO configuracion(clave) VALUES ('inicializada')")


# ==========================================
# PRODUCTOS
# ==========================================

def _producto(fila) -> dict:
    datos = dict(fila)
    # El campo disponible no se almacena, se deduce del stock.
    datos["disponible"] = datos["stock"] > 0
    return datos


def _buscar_producto(con, id_producto: int) -> dict:
    fila = con.execute("SELECT * FROM productos WHERE id=?", (id_producto,)).fetchone()
    if fila is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return _producto(fila)


def listar_productos(categoria=None, disponible=None) -> list[dict]:
    with conexion() as con:
        filas = con.execute(
            "SELECT * FROM productos WHERE (? IS NULL OR categoria=?) ORDER BY id",
            (categoria, categoria)
        ).fetchall()
    productos = [_producto(f) for f in filas]
    if disponible is not None:
        productos = [p for p in productos if p["disponible"] == disponible]
    return productos


def obtener_producto(id_producto: int) -> dict:
    with conexion() as con:
        return _buscar_producto(con, id_producto)


def crear_producto(datos: dict) -> dict:
    with conexion(True) as con:
        # Un producto se considera repetido si coinciden nombre y categoría.
        nombre = datos["nombre"].strip().lower()
        for fila in con.execute("SELECT nombre FROM productos WHERE categoria=?",
                                (datos["categoria"],)):
            if fila["nombre"].strip().lower() == nombre:
                raise HTTPException(status_code=409,
                                    detail="Ya existe un producto con esos datos")
        cursor = con.execute(
            "INSERT INTO productos(nombre,descripcion,categoria,precio,stock,imagen) "
            "VALUES (?,?,?,?,?,?)",
            (datos["nombre"], datos.get("descripcion"), datos["categoria"],
             datos["precio"], datos["stock"], datos.get("imagen")))
        return _buscar_producto(con, cursor.lastrowid)


def modificar_producto(id_producto: int, datos: dict) -> dict:
    with conexion(True) as con:
        _buscar_producto(con, id_producto)
        con.execute(
            "UPDATE productos SET nombre=?,descripcion=?,categoria=?,precio=?,stock=?,imagen=? "
            "WHERE id=?",
            (datos["nombre"], datos.get("descripcion"), datos["categoria"],
             datos["precio"], datos["stock"], datos.get("imagen"), id_producto))
        return _buscar_producto(con, id_producto)


def eliminar_producto(id_producto: int) -> None:
    with conexion(True) as con:
        _buscar_producto(con, id_producto)
        if con.execute("SELECT 1 FROM compras WHERE idProducto=? LIMIT 1",
                       (id_producto,)).fetchone():
            raise HTTPException(status_code=409,
                                detail="El producto tiene compras asociadas")
        con.execute("DELETE FROM productos WHERE id=?", (id_producto,))


def actualizar_stock(id_producto: int, stock: int) -> dict:
    with conexion(True) as con:
        _buscar_producto(con, id_producto)
        con.execute("UPDATE productos SET stock=? WHERE id=?", (stock, id_producto))
        return _buscar_producto(con, id_producto)


# ==========================================
# COMPRAS
# ==========================================

def _buscar_compra(con, id_compra: int) -> dict:
    fila = con.execute("SELECT * FROM compras WHERE idCompra=?", (id_compra,)).fetchone()
    if fila is None:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    return dict(fila)


def registrar_compra(id_usuario: int, id_producto: int, cantidad: int, talla) -> dict:
    with conexion(True) as con:
        producto = _buscar_producto(con, id_producto)

        # La talla solo se exige en las categorías que la necesitan
        if producto["categoria"] in CATEGORIAS_CON_TALLA and talla is None:
            raise HTTPException(status_code=400,
                                detail="Es necesario indicar la talla para este producto")
        if producto["categoria"] not in CATEGORIAS_CON_TALLA and talla is not None:
            raise HTTPException(status_code=400,
                                detail="Este producto no admite talla")

        if producto["stock"] < cantidad:
            raise HTTPException(status_code=409,
                                detail="No hay suficiente stock disponible")

        # Descuenta el stock y crea la compra en la misma transacción
        con.execute("UPDATE productos SET stock=stock-? WHERE id=?", (cantidad, id_producto))
        cursor = con.execute(
            "INSERT INTO compras(idUsuario,idProducto,cantidad,talla,precioTotal,fechaCompra,estado) "
            "VALUES (?,?,?,?,?,?,?)",
            (id_usuario, id_producto, cantidad, talla,
             round(producto["precio"] * cantidad, 2),
             datetime.now(timezone.utc).isoformat(), "realizada"))
        return _buscar_compra(con, cursor.lastrowid)


def obtener_compra(id_compra: int) -> dict:
    with conexion() as con:
        return _buscar_compra(con, id_compra)


def compras_de_usuario(id_usuario: int) -> list[dict]:
    with conexion() as con:
        filas = con.execute("SELECT * FROM compras WHERE idUsuario=? ORDER BY idCompra",
                            (id_usuario,)).fetchall()
    return [dict(f) for f in filas]


def cancelar_compra(id_compra: int) -> dict:
    with conexion(True) as con:
        compra = _buscar_compra(con, id_compra)
        if compra["estado"] == "cancelada":
            raise HTTPException(status_code=409, detail="La compra ya está cancelada")
        if compra["estado"] == "entregada":
            raise HTTPException(status_code=409,
                                detail="Una compra entregada no puede cancelarse")
        con.execute("UPDATE compras SET estado='cancelada' WHERE idCompra=?", (id_compra,))
        # Devolver el stock al producto
        con.execute("UPDATE productos SET stock=stock+? WHERE id=?",
                    (compra["cantidad"], compra["idProducto"]))
        return _buscar_compra(con, id_compra)
