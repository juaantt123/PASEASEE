@echo off
cd /d "%~dp0"

:: --- VARIABLES DE ENTORNO (AUTOMATIZADAS) ---
:: 1. Clave interna para que la API de Estadísticas no dé error
set CLAVE_INTERNA_ESTADISTICAS=clave_estadisticas_123

:: 2. Credenciales de administrador para la API de Usuarios
set SUBSONIC_ADMIN_EMAIL=admin@subsonic.com
set SUBSONIC_ADMIN_PASSWORD=admin12345

if not exist ".venv\Scripts\python.exe" (
    echo No se encuentra .venv. Instala las dependencias siguiendo el README.
    pause
    exit /b 1
)

start "API Entradas" cmd /k ""%~dp0.venv\Scripts\python.exe" -m uvicorn Entradas.main_entradas:app --port 8000 --reload"
start "API Usuarios" cmd /k ""%~dp0.venv\Scripts\python.exe" -m uvicorn Usuarios.main_usuario:app --port 8001 --reload"
start "API Escaleta" cmd /k ""%~dp0.venv\Scripts\python.exe" -m uvicorn Escaleta.main_escaleta:app --port 8002 --reload"
start "API Espacios" cmd /k ""%~dp0.venv\Scripts\python.exe" -m uvicorn Espacios.main_espacios:app --port 8003 --reload"
start "API Merchandising" cmd /k ""%~dp0.venv\Scripts\python.exe" -m uvicorn Merchandising.main_tienda:app --port 8004 --reload"
start "API Estadisticas" cmd /k ""%~dp0.venv\Scripts\python.exe" -m uvicorn Estadisticas.main_estadisticas:app --port 8005 --reload"

echo Iniciando todos los microservicios... ¡Listo!