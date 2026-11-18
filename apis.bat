@echo off
cd /d "%~dp0"

:: --- VARIABLES DE ENTORNO (AUTOMATIZADAS) ---
:: 1. Clave interna para que la API de Estadísticas no dé error
if not defined CLAVE_INTERNA_ESTADISTICAS (echo Configura CLAVE_INTERNA_ESTADISTICAS. & exit /b 1)

:: 2. Credenciales de administrador para la API de Usuarios
if not defined SUBSONIC_ADMIN_EMAIL (echo Configura SUBSONIC_ADMIN_EMAIL. & exit /b 1)
if not defined SUBSONIC_ADMIN_PASSWORD (echo Configura SUBSONIC_ADMIN_PASSWORD. & exit /b 1)

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