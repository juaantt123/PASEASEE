import importlib

import pytest
from fastapi.testclient import TestClient

from scripts.probar_e2e import MODULOS


@pytest.fixture
def servicio(monkeypatch, tmp_path):
    """Reinicia la memoria del servicio y aísla cada SQLite de los datos locales."""
    monkeypatch.setenv("ENTRADAS_DB", str(tmp_path / "entradas.sqlite3"))
    monkeypatch.setenv("ESCALETA_DB", str(tmp_path / "escaleta.sqlite3"))

    def cargar(nombre):
        modulo = importlib.reload(importlib.import_module(MODULOS[nombre]))
        # rutas_sqlite conserva las funciones del módulo de persistencia; esas
        # funciones consultan DB_PATH en cada llamada.
        if nombre == "Entradas":
            monkeypatch.setattr(importlib.import_module("Entradas.persistencia"),
                               "DB_PATH", tmp_path / "entradas.sqlite3")
        return modulo, TestClient(modulo.app)

    return cargar
