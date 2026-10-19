from fastapi import FastAPI

app = FastAPI(title="Subsonic Festival - Entradas")

@app.get("/")
def inicio():
    return {"mensaje": "Microservicio de Entradas funcionando"}
