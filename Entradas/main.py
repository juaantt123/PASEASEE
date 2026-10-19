from fastapi import FastAPI, HTTPException

app = FastAPI(title="Subsonic Festival - Entradas")

# Datos provisionales hasta conectar la base de datos
entradas = [
    {"id": 1, "tipo": "vip", "precio": 150},
    {"id": 2, "tipo": "abono_completo", "precio": 90},
    {"id": 3, "tipo": "abono_un_dia", "precio": 40}
]

@app.get("/")
def inicio():
    return {"mensaje": "Microservicio de Entradas funcionando"}

@app.get("/entradas")
def listar_entradas():
    return entradas

@app.get("/entradas/{id_entrada}")
def obtener_entrada(id_entrada: int):
    for entrada in entradas:
        if entrada["id"] == id_entrada:
            return entrada

    raise HTTPException(
        status_code=404,
        detail="Entrada no encontrada"
    )
