import importlib

import pytest
from fastapi.testclient import TestClient

from scripts.probar_e2e import MODULOS


@pytest.fixture
def servicio(monkeypatch, tmp_path):
    """Reinicia la memoria del servicio y aísla cada SQLite de los datos locales."""
    monkeypatch.setenv("ENTRADAS_DB", str(tmp_path / "entradas.sqlite3"))
    monkeypatch.setenv("ESCALETA_DB", str(tmp_path / "escaleta.sqlite3"))
    monkeypatch.setenv("MERCHANDISING_DB", str(tmp_path / "merchandising.sqlite3"))

    def cargar(nombre):
        # Estos módulos de persistencia no se recargan con el servicio y fijan
        # DB_PATH al importarse: se redirigen a un SQLite temporal antes de
        # recargar, para que las pruebas no escriban en los datos locales.
        for persistencia, archivo in (("Entradas.persistencia", "entradas"),
                                      ("Usuarios.persistencia_usuarios", "usuarios"),
                                      ("Espacios.persistencia_espacios", "espacios")):
            monkeypatch.setattr(importlib.import_module(persistencia),
                               "DB_PATH", tmp_path / f"{archivo}.sqlite3")
        modulo = importlib.reload(importlib.import_module(MODULOS[nombre]))
        return modulo, TestClient(modulo.app)

    return cargar
