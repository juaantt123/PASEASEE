import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.getenv(
    'USUARIOS_DB',
    Path(__file__).resolve().parent / 'data' / 'usuarios.sqlite3'
))


def conectar():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys = ON')
    con.execute('PRAGMA busy_timeout = 15000')
    return con


def inicializar():
    with conectar() as con:
        con.executescript('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                apellidos TEXT NOT NULL,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                telefono TEXT,
                fechaNacimiento TEXT,
                tipo TEXT NOT NULL CHECK(tipo IN ('cliente','proveedor','administrador')),
                fotoPerfil TEXT,
                fechaRegistro TEXT NOT NULL,
                salt TEXT,
                hash_password TEXT,
                saldo_centimos INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS metodos_pago (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                idUsuario INTEGER NOT NULL,
                tipo TEXT NOT NULL CHECK(tipo IN ('tarjeta','paypal')),
                titular TEXT,
                ultimosDigitos TEXT,
                predeterminado INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(idUsuario) REFERENCES usuarios(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS configuracion (
                clave TEXT PRIMARY KEY,
                valor TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sesiones (
                token_hash TEXT PRIMARY KEY,
                idUsuario INTEGER NOT NULL,
                FOREIGN KEY(idUsuario) REFERENCES usuarios(id) ON DELETE CASCADE
            );
        ''')
        # Usuario de demostracion que ya utiliza la integracion de Entradas.
        # Solo se crea si no existe; nunca se sobrescriben datos anteriores.
        if con.execute("SELECT 1 FROM configuracion WHERE clave='datos_iniciales'").fetchone() is None:
            con.execute("INSERT INTO configuracion (clave,valor) VALUES ('datos_iniciales','1')")
            con.execute('''
                INSERT INTO usuarios
                (id,nombre,apellidos,email,tipo,fechaRegistro)
                VALUES(25,'Laura','Garcia Sanchez','laura@email.com','cliente',
                       '2027-04-10T12:30:00+00:00')
            ''')
            con.execute('''
                INSERT INTO metodos_pago
                (id,idUsuario,tipo,titular,ultimosDigitos,predeterminado)
                VALUES(4,25,'tarjeta','Laura Garcia Sanchez','4582',1)
            ''')
