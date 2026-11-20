@echo off
cd /d "%~dp0"

:: --- VARIABLES DE ENTORNO ---
if not defined CLAVE_INTERNA_ESTADISTICAS set "CLAVE_INTERNA_ESTADISTICAS=clave_local_dev"
if not defined SUBSONIC_ADMIN_EMAIL set "SUBSONIC_ADMIN_EMAIL=admin1@subsonic.com"
if not defined SUBSONIC_ADMIN_PASSWORD set "SUBSONIC_ADMIN_PASSWORD=admin123"

:: Usa .venv si existe; si no, usa el python global
set "PYTHON_CMD=python"
if exist "%~dp0.venv\Scripts\python.exe" set "PYTHON_CMD=%~dp0.venv\Scripts\python.exe"

start "API Entradas" cmd /k ""%PYTHON_CMD%" -m uvicorn Entradas.main_entradas:app --port 8000 --reload"
start "API Usuarios" cmd /k ""%PYTHON_CMD%" -m uvicorn Usuarios.main_usuario:app --port 8001 --reload"
start "API Escaleta" cmd /k ""%PYTHON_CMD%" -m uvicorn Escaleta.main_escaleta:app --port 8002 --reload"
start "API Espacios" cmd /k ""%PYTHON_CMD%" -m uvicorn Espacios.main_espacios:app --port 8003 --reload"
start "API Merchandising" cmd /k ""%PYTHON_CMD%" -m uvicorn Merchandising.main_tienda:app --port 8004 --reload"
start "API Estadisticas" cmd /k ""%PYTHON_CMD%" -m uvicorn Estadisticas.main_estadisticas:app --port 8005 --reload"

echo Iniciando todos los microservicios... ¡Listo!
pause