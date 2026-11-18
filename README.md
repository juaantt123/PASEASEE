# Subsonic Festival - Práctica 2

El proyecto contiene servicios FastAPI para Entradas, Usuarios, Escaleta, Espacios, Merchandising y Estadísticas, y una interfaz web en `view/`. Usuarios, Entradas, Escaleta, Espacios y Merchandising almacenan datos en bases SQLite locales. Estadísticas consulta los demás servicios.

## Preparación en Windows

Desde PowerShell, en la raíz del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-test.txt
```

## Arranque

Configura en cada terminal que arranque los servicios una clave compartida y las credenciales para crear el administrador inicial:

```powershell
$env:CLAVE_INTERNA_ESTADISTICAS = "clave-local-de-ejemplo"
$env:SUBSONIC_ADMIN_EMAIL = "admin@example.test"
$env:SUBSONIC_ADMIN_PASSWORD = "elige-una-clave-local"
.\apis.bat
```

La primera vez se crea el administrador si no existe una cuenta con ese correo. Las variables no cambian la contraseña ni el rol de cuentas ya existentes. Usa tus propios valores y no los subas a Git. Para arrancar servicios manualmente, configura las mismas variables en sus terminales.

En otra terminal, ejecuta ` .\.venv\Scripts\python.exe -m http.server 5500 --directory view` y abre http://127.0.0.1:5500/. Inicia sesión con el administrador en Perfil para acceder al panel. El perfil consulta la programación de Escaleta.

| Servicio | Puerto | Documentación |
| --- | --- | --- |
| Entradas | 8000 | http://127.0.0.1:8000/docs |
| Usuarios | 8001 | http://127.0.0.1:8001/docs |
| Escaleta | 8002 | http://127.0.0.1:8002/docs |
| Espacios | 8003 | http://127.0.0.1:8003/docs |
| Merchandising | 8004 | http://127.0.0.1:8004/docs |
| Estadísticas | 8005 | http://127.0.0.1:8005/docs |

Los archivos SQLite se crean en las carpetas `data` de cada servicio y no se suben a Git. Cada compañero tiene sus propios datos. Las variables `USUARIOS_DB`, `ENTRADAS_DB`, `ESCALETA_DB`, `ESPACIOS_DB` y `MERCHANDISING_DB` permiten seleccionar otras rutas para las bases de datos.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unitarios -v
.\.venv\Scripts\python.exe -m pytest tests/integracion -v
```

Las pruebas de integración arrancan sus servicios con bases temporales y un administrador de pruebas. El saldo y las compras son demostrativos; no se realizan cobros reales.

## Proveedores

Un proveedor crea primero una cuenta normal en Perfil. Un administrador inicia sesión, abre **Proveedores** en el panel y asigna el rol a esa cuenta. El proveedor entra desde Perfil con su propio correo y contraseña; se abrirá su área de productos. Puede crear, editar y eliminar sus productos; no puede modificar productos de otros proveedores. Los productos existentes sin proveedor siguen administrados desde el panel. No se pueden eliminar productos con compras asociadas.

Las rutas protegidas de Merchandising son `/api/merchandising/proveedor/productos` (GET, POST) y `/api/merchandising/proveedor/productos/{idProducto}` (PUT, DELETE). Requieren una sesión de proveedor válida. La actualización de una base existente añade automáticamente la columna de propietario sin borrar los productos.
