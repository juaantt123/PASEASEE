# Subsonic Festival - Práctica 2

El proyecto contiene APIs independientes para Usuarios, Entradas, Espacios, Escaleta, Merchandising y Estadísticas, además de la interfaz web en `view/`. La API de Escaleta usa SQLite; los demás servicios mantienen actualmente sus datos en memoria.

## Preparar el entorno

Abre PowerShell en la carpeta `PASEASEE-main` y prepara un entorno Python común para los servicios:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Probar compra de entradas desde la interfaz

Abre tres ventanas de PowerShell. Ejecuta cada comando desde la carpeta `PASEASEE-main`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn Usuarios.main:app --reload --port 8001
```

```powershell
.\.venv\Scripts\python.exe -m uvicorn Entradas.main:app --reload --port 8000
```

```powershell
.\.venv\Scripts\python.exe -m http.server 5500 --directory view
```

Abre `http://127.0.0.1:5500/`. En **Perfil**, crea una cuenta e inicia sesión. En **Entradas**, el catálogo y los precios provienen de la API; selecciona una entrada y continúa. El formulario pide datos ficticios de tarjeta, crea un método de pago de prueba en Usuarios y registra la compra en Entradas. No se realiza ningún cobro. Después puedes consultar tus entradas en Perfil.

Para comprobar las APIs directamente, abre `http://127.0.0.1:8001/docs` (Usuarios) y `http://127.0.0.1:8000/docs` (Entradas). También se puede comprobar el stock en `GET /api/entradas/disponibles` antes y después de una compra.

## Puertos de desarrollo

| Componente | Puerto |
| --- | ---: |
| Entradas | 8000 |
| Usuarios | 8001 |
| Escaleta | 8002 |
| Espacios | 8003 |
| Merchandising | 8004 |
| Estadísticas | 8005 |
| Interfaz web | 5500 |

Escaleta consulta Espacios en `http://127.0.0.1:8003/api` por defecto. Las dependencias y direcciones se pueden cambiar mediante las variables de entorno que leen los módulos.

## Estado observado y continuación

El PDF sitúa el trabajo en una progresión de estructura y lógica, persistencia, interfaz y pruebas, y después correcciones. En esta copia se conectó el flujo del catálogo y compra de Entradas con Usuarios y Entradas; Escaleta ya persiste en SQLite. La persistencia de los otros componentes y la integración de la tienda de merchandising con su API siguen siendo trabajo pendiente.
