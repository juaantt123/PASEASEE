const API_ESTADISTICAS = 'http://127.0.0.1:8005/api/estadisticas';

function sesionEstadisticas() {
    try { return JSON.parse(sessionStorage.getItem('subsonic-sesion')); }
    catch { return null; }
}

function tarjetaEstadistica(label, valor) {
    const tarjeta = document.createElement('article');
    tarjeta.className = 'stats-card';
    const texto = document.createElement('span');
    const cifra = document.createElement('strong');
    texto.textContent = label;
    cifra.textContent = valor;
    tarjeta.append(texto, cifra);
    return tarjeta;
}

function detalleEstadistica(titulo, filas) {
    const tarjeta = document.createElement('article');
    tarjeta.className = 'card';
    const heading = document.createElement('h3');
    heading.textContent = titulo;
    tarjeta.appendChild(heading);
    for (const [etiqueta, valor] of filas) {
        const fila = document.createElement('div');
        fila.className = 'stats-row';
        const texto = document.createElement('span');
        const cifra = document.createElement('strong');
        texto.textContent = etiqueta;
        cifra.textContent = valor;
        fila.append(texto, cifra);
        tarjeta.appendChild(fila);
    }
    return tarjeta;
}

async function cargarEstadisticas() {
    const estado = document.getElementById('stats-status');
    const resumen = document.getElementById('stats-summary');
    const detalles = document.getElementById('stats-details');
    const sesion = sesionEstadisticas();
    resumen.replaceChildren();
    detalles.replaceChildren();
    if (!sesion?.token) {
        estado.textContent = 'Inicia sesión como administrador para consultar las estadísticas.';
        return;
    }
    estado.textContent = 'Cargando estadísticas…';
    const rutas = ['resumen', 'entradas', 'ingresos', 'usuarios', 'merchandising', 'espacios', 'artistas', 'ventas-por-dia'];
    const respuestas = await Promise.allSettled(rutas.map(async ruta => {
        const respuesta = await fetch(`${API_ESTADISTICAS}/${ruta}`, {
            headers: { Authorization: `Bearer ${sesion.token}` }
        });
        if (!respuesta.ok) {
            let mensaje = `Error ${respuesta.status}`;
            try { mensaje = (await respuesta.json()).mensaje || mensaje; } catch {}
            throw new Error(mensaje);
        }
        return respuesta.json();
    }));
    const datos = Object.fromEntries(rutas.map((ruta, i) => [ruta, respuestas[i].status === 'fulfilled' ? respuestas[i].value : null]));
    const fallos = rutas.filter((_, i) => respuestas[i].status === 'rejected');
    if (fallos.length) {
        const primero = respuestas[rutas.indexOf(fallos[0])].reason;
        estado.textContent = `No se pudieron cargar: ${fallos.join(', ')}. ${primero?.message || 'Comprueba los servicios.'}`;
    } else {
        estado.textContent = 'Datos actualizados. Los importes corresponden a operaciones de demostración.';
    }
    const dinero = n => `${Number(n).toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €`;
    if (datos.resumen) {
        const r = datos.resumen;
        for (const [label, valor] of [['Usuarios', r.totalUsuarios], ['Entradas vendidas', r.entradasVendidas], ['Ingresos totales', dinero(r.ingresosTotales)], ['Actuaciones', r.totalActuaciones], ['Artistas', r.totalArtistas], ['Espacios', r.totalEspacios]]) {
            resumen.append(tarjetaEstadistica(label, valor));
        }
    }
    if (datos.entradas) {
        const d = datos.entradas;
        detalles.append(detalleEstadistica('Entradas', [['Vendidas', d.totalVendidas], ['Un día', d.abonosUnDia], ['Abonos completos', d.abonosCompletos], ['VIP', d.entradasVIP], ['Ingresos', dinero(d.ingresos)], ['Porcentaje vendido', `${d.porcentajeVendido} %`]]));
    }
    if (datos.ingresos) {
        const d = datos.ingresos;
        detalles.append(detalleEstadistica('Ingresos', [['Entradas', dinero(d.ingresosEntradas)], ['Merchandising', dinero(d.ingresosMerchandising)], ['Total', dinero(d.ingresosTotales)]]));
    }
    if (datos.usuarios) {
        const d = datos.usuarios;
        detalles.append(detalleEstadistica('Usuarios', [['Total', d.totalUsuarios], ['Clientes', d.clientes], ['Proveedores', d.proveedores], ['Administradores', d.administradores]]));
    }
    if (datos.merchandising) {
        const d = datos.merchandising;
        detalles.append(detalleEstadistica('Merchandising', [['Productos vendidos', d.productosVendidos], ['Ingresos', dinero(d.ingresos)], ['Producto más vendido', d.productoMasVendido || 'Sin ventas']]));
    }
    if (datos.espacios) detalles.append(detalleEstadistica('Uso de espacios', datos.espacios.length ? datos.espacios.map(e => [e.nombreEspacio, `${e.numeroEventos} eventos · ${e.horasUso} h`]) : [['Espacios', 'Sin datos']]));
    if (datos.artistas) detalles.append(detalleEstadistica('Actuaciones por artista', datos.artistas.length ? datos.artistas.map(a => [a.nombreArtista, a.numeroActuaciones]) : [['Artistas', 'Sin datos']]));
    if (datos['ventas-por-dia']) detalles.append(detalleEstadistica('Ventas por día', datos['ventas-por-dia'].length ? datos['ventas-por-dia'].map(v => [v.fecha, `${v.numeroVentas} compras · ${dinero(v.ingresos)}`]) : [['Ventas', 'Sin datos']]));
}

document.getElementById('stats-refresh').addEventListener('click', cargarEstadisticas);
