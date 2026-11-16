# Subsonic Festival · Pruebas de la semana 3

## Ejecución en Windows (Git Bash)

Desde la raíz de PASEASEE, donde está `requirements.txt`:

```bash
# Solo si .venv aún no existe:
py -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements-test.txt
python -m pytest -q -rx
python scripts/probar_e2e.py
```

Si ya tienes el entorno, empieza por `source`. La integración y el script arrancan los
seis servicios en puertos locales temporales y los detienen al terminar. No hace falta
ejecutar `apis.bat` ni abrir Swagger. Entradas y Escaleta usan SQLite temporales;
las compras no implican cobro real. El script prueba las APIs, no la interfaz del navegador.

Para ejecutarlas por separado:

```bash
python -m pytest -q tests/unitarios
python -m pytest -q -rx tests/integracion
```

## Qué se comprueba

| Servicio | 200 | 400 | 404 | 409 | 503 |
|---|---|---|---|---|---|
| Usuarios | Consulta tras alta | Contraseña demasiado corta | Usuario inexistente | Correo duplicado | Sin dependencia remota |
| Entradas | Consulta tras compra | Medio de pago ajeno | Tipo de entrada inexistente | Stock insuficiente | Usuarios no responde |
| Merchandising | Consulta tras compra | Falta talla | Producto inexistente | Stock insuficiente | Usuarios no responde |
| Espacios | Consulta tras alta | Franja invertida | Espacio inexistente | Nombre duplicado | Escaleta no responde |
| Escaleta | Consulta filtrada | Franja invertida | Artista inexistente | Solapamiento; las franjas contiguas se aceptan | Espacios no responde |
| Estadísticas | Recuento por tipo de usuario | Periodo invertido | Recomendación para usuario inexistente | Las consultas probadas no modifican datos | Formato recibido inválido |

También se comprueba la persistencia de una compra y del stock de Entradas al volver
a iniciar la aplicación con el mismo SQLite temporal. Las pruebas por servicio se
ejecutan con pytest y TestClient, sustituyendo las respuestas de dependencias remotas.

La integración usa HTTP real entre procesos separados:

1. **Entradas ↔ Usuarios:** alta, login, método de pago, compra, códigos de las entradas,
   stock, validación y cancelación. Verifica consulta propia con Bearer, 401 sin sesión
   y 403 al consultar entradas de otro usuario.
2. **Merchandising ↔ Usuarios:** compra, consulta y cancelación; el stock se repone una vez.
3. **Espacios ↔ Escaleta:** escenario libre, ocupado tras programar, rechazo del
   solapamiento y disponibilidad al cancelar. Estadísticas refleja los cambios de uso.
4. **Estadísticas ↔ Usuarios y Merchandising:** el alta y la venta cambian los
   agregados; la cancelación devuelve ventas e ingresos a sus valores iniciales.

## Resultado y fallo conocido

**33 pruebas pasan** (29 por servicio y 4 de integración). Una prueba de integración
adicional se marca como **`XFAIL` estricto**. `GET /api/estadisticas/resumen`
solicita `GET /api/entradas/usuarios/{idUsuario}` sin una sesión del propietario.
Entradas responde 401 y Estadísticas lo comunica como 503. También quedan afectados
los demás agregados que reutilizan esa consulta; además, la implementación actual
indica que necesita una fuente de importes históricos de Entradas. Para corregirlo
habría que acordar un acceso entre servicios y un contrato de datos de ventas, sin
abrir el acceso a las entradas privadas de los usuarios.

La prueba solo admite ese fallo concreto. Si aparece un error distinto o el resumen
empieza a funcionar, pytest lo señala para que se revise la marca. El script
independiente avisa de ese pendiente. Para que lo trate como fallo y salga con
código 1, usa `python scripts/probar_e2e.py --estricto`.

## Incorporar al repositorio compartido

El ZIP incluye el código de la versión actual y las adiciones. Para integrarlas en tu
clon, copia únicamente `tests/`, `scripts/probar_e2e.py`, `pytest.ini`,
`requirements-test.txt`, `PRUEBAS_SEMANA_3.md` y las reglas nuevas de `.gitignore`.
Si tu clon ya tiene cambios en estos archivos, revísalos antes de reemplazarlos.

Las bases locales, la caché, el entorno virtual y el historial de Git se excluyen del
ZIP. Git ignora los SQLite nuevos bajo cualquier carpeta `data/`. Si ya había un
SQLite versionado, añadir `.gitignore` no lo deja de rastrear. El equipo puede
acordar retirarlo del índice en un commit separado, con copia de respaldo, para
evitar que vuelva a bloquear un pull.
