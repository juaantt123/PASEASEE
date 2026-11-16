"""Persistencia local SQLite para el microservicio Espacios."""
from pathlib import Path
import os
import sqlite3

DB_PATH = Path(os.getenv("ESPACIOS_DB", Path(__file__).parent / "data" / "espacios.sqlite3"))


def conexion():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def inicializar(Espacio):
    with conexion() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS espacios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL COLLATE NOCASE UNIQUE,
            tipo TEXT NOT NULL, ubicacion TEXT NOT NULL,
            capacidad INTEGER NOT NULL CHECK(capacidad >= 1),
            tamano INTEGER NOT NULL CHECK(tamano >= 1),
            descripcion TEXT, estado TEXT NOT NULL
        )""")
        if con.execute("SELECT COUNT(*) FROM espacios").fetchone()[0] == 0:
            con.executemany("""INSERT INTO espacios
                (id,nombre,tipo,ubicacion,capacidad,tamano,descripcion,estado)
                VALUES (?,?,?,?,?,?,?,?)""", [
                (1, "Escenario Principal", "escenario", "Zona Norte", 15000, 1200,
                 "Escenario principal destinado a los conciertos de mayor afluencia.", "activo"),
                (2, "Zona de Restauración", "restauracion", "Zona Central", 2500, 350,
                 "Área de puestos de comida y bebida.", "activo"),
            ])
    return Espacio


def convertir(fila, Espacio):
    return Espacio(**dict(fila))


def listar(Espacio, tipo=None, estado=None):
    sql, valores = "SELECT * FROM espacios", []
    filtros = []
    if tipo is not None:
        filtros.append("tipo = ?"); valores.append(tipo)
    if estado is not None:
        filtros.append("estado = ?"); valores.append(estado)
    if filtros:
        sql += " WHERE " + " AND ".join(filtros)
    with conexion() as con:
        return [convertir(f, Espacio) for f in con.execute(sql, valores)]


def obtener(id_espacio, Espacio):
    with conexion() as con:
        fila = con.execute("SELECT * FROM espacios WHERE id=?", (id_espacio,)).fetchone()
    return convertir(fila, Espacio) if fila else None


def crear(datos, Espacio):
    valores = datos.model_dump()
    with conexion() as con:
        cur = con.execute("""INSERT INTO espacios
            (nombre,tipo,ubicacion,capacidad,tamano,descripcion,estado)
            VALUES (:nombre,:tipo,:ubicacion,:capacidad,:tamano,:descripcion,:estado)""", valores)
        fila = con.execute("SELECT * FROM espacios WHERE id=?", (cur.lastrowid,)).fetchone()
    return convertir(fila, Espacio)


def actualizar(id_espacio, datos, Espacio):
    valores = datos.model_dump()
    with conexion() as con:
        con.execute("""UPDATE espacios SET nombre=:nombre,tipo=:tipo,ubicacion=:ubicacion,
            capacidad=:capacidad,tamano=:tamano,descripcion=:descripcion,estado=:estado WHERE id=:id""",
            {**valores, "id": id_espacio})
    return obtener(id_espacio, Espacio)


def actualizar_campo(id_espacio, campo, valor, Espacio):
    if campo not in {"estado", "capacidad"}:
        raise ValueError("Campo no permitido")
    with conexion() as con:
        con.execute(f"UPDATE espacios SET {campo}=? WHERE id=?", (valor, id_espacio))
    return obtener(id_espacio, Espacio)


def eliminar(id_espacio):
    with conexion() as con:
        cur = con.execute("DELETE FROM espacios WHERE id=?", (id_espacio,))
        return cur.rowcount > 0
