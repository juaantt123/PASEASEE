"""Persistencia SQLite del servicio de entradas."""
from contextlib import contextmanager
from pathlib import Path
import os
import sqlite3

DB_PATH = Path(os.getenv("ENTRADAS_DB", Path(__file__).parent / "data" / "entradas.sqlite3"))


@contextmanager
def conexion(escritura=False):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        if escritura:
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
        con.execute("CREATE TABLE IF NOT EXISTS tipos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL UNIQUE, descripcion TEXT NOT NULL, precio REAL NOT NULL, stockTotal INTEGER NOT NULL, stockDisponible INTEGER NOT NULL, fechaInicioValidez TEXT NOT NULL, fechaFinValidez TEXT NOT NULL, estado TEXT NOT NULL)")
        con.execute("CREATE TABLE IF NOT EXISTS compras (idCompra INTEGER PRIMARY KEY AUTOINCREMENT, idUsuario INTEGER NOT NULL, idTipoEntrada INTEGER NOT NULL REFERENCES tipos(id), tipoEntrada TEXT NOT NULL, cantidad INTEGER NOT NULL, precioTotal REAL NOT NULL, fechaCompra TEXT NOT NULL, estado TEXT NOT NULL)")
        con.execute("CREATE TABLE IF NOT EXISTS entradas (idEntrada INTEGER PRIMARY KEY AUTOINCREMENT, idCompra INTEGER NOT NULL REFERENCES compras(idCompra), idUsuario INTEGER NOT NULL, idTipoEntrada INTEGER NOT NULL REFERENCES tipos(id), tipoEntrada TEXT NOT NULL, codigo TEXT UNIQUE, fechaCompra TEXT NOT NULL, fechaInicioValidez TEXT NOT NULL, fechaFinValidez TEXT NOT NULL, estado TEXT NOT NULL)")
        con.execute("CREATE TABLE IF NOT EXISTS configuracion (clave TEXT PRIMARY KEY)")
        if not con.execute("SELECT 1 FROM configuracion WHERE clave = 'inicializada'").fetchone():
            con.executemany("INSERT INTO tipos(nombre,descripcion,precio,stockTotal,stockDisponible,fechaInicioValidez,fechaFinValidez,estado) VALUES (?,?,?,?,?,?,?,?)", [
                ("vip", "Acceso VIP al festival", 150, 1000, 1000, "2027-07-15", "2027-07-18", "disponible"),
                ("abono_completo", "Acceso todos los dias", 90, 5000, 5000, "2027-07-15", "2027-07-18", "disponible"),
                ("abono_un_dia", "Acceso al festival durante un día", 25, 3000, 3000, "2027-07-16", "2027-07-16", "disponible"),
            ])
            con.execute("INSERT INTO configuracion VALUES ('inicializada')")
