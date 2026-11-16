@echo off
echo Iniciando todos los microservicios de Subsonic Festival...

:: API Entradas (Puerto 8000)
start "API Entradas" cmd /k "cd Entradas && "python -m uvicorn main_entradas:app --port 8000 --reload"

:: API Usuarios (Puerto 8001)
start "API Usuarios" cmd /k "cd Usuarios && "python -m uvicorn main_usuario:app --port 8001 --reload"

:: API Escaleta (Puerto 8002)
start "API Escaleta" cmd /k "cd Escaleta && "python -m uvicorn main_escaleta:app --port 8002 --reload"

:: API Espacios (Puerto 8003)
start "API Espacios" cmd /k "cd Espacios && "python -m uvicorn main_espacios:app --port 8003 --reload"

:: API Tienda / Merchandising (Puerto 8004)
start "API Tienda" cmd /k "cd Tienda && "python -m uvicorn main_tienda:app --port 8004 --reload"

:: API Estadisticas (Puerto 8005)
start "API Estadisticas" cmd /k "cd Estadisticas && "python -m uvicorn main_estadisticas:app --port 8005 --reload"

echo Las APIs se estan iniciando en ventanas separadas.