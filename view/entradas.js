const API_ENTRADAS_CATALOGO = [
    window.SUBSONIC_ENTRADAS_API_URL,
    'http://127.0.0.1:8000/api/entradas',
    'http://localhost:8000/api/entradas',
    'http://127.0.0.1:8081/api/entradas'
].filter(Boolean);

const PRESENTACION_ENTRADAS = {
    abono_un_dia: {
        titulo: 'Entrada de día',
        etiqueta: 'UN DÍA',
        icono: '◷',
        descripcion: 'Acceso al festival durante un día.',
        ventajas: ['Acceso durante las fechas indicadas', 'Entrada personal con código']
    },
    abono_completo: {
        titulo: 'Abono general',
        etiqueta: 'TRES DÍAS',
        icono: '✦',
        descripcion: 'Acceso al festival durante todos sus días.',
        ventajas: ['Acceso durante todo el festival', 'Entrada personal con código'],
        destacado: true
    },
    vip: {
        titulo: 'Abono VIP',
        etiqueta: 'EXPERIENCIA VIP',
        icono: '✧',
        descripcion: 'Acceso VIP al festival.',
        ventajas: ['Acceso durante las fechas indicadas', 'Entrada personal con código']
    }
};

document.addEventListener('DOMContentLoaded', cargarCatalogoEntradas);

async function cargarCatalogoEntradas() {
    const catalogo = document.getElementById('ticket-catalog');
    if (!catalogo) return;

    try {
        const tipos = await solicitarApiEntradas('/disponibles');
        catalogo.replaceChildren();
        const orden = { abono_un_dia: 0, abono_completo: 1, vip: 2 };
        tipos.sort((a, b) => (orden[a.nombre] ?? 9) - (orden[b.nombre] ?? 9));

        if (tipos.length === 0) {
            catalogo.textContent = 'No hay entradas disponibles en este momento.';
            return;
        }

        tipos.forEach((tipo) => catalogo.appendChild(crearTarjetaEntrada(tipo)));
    } catch (error) {
        catalogo.textContent = `No se pudo cargar el catálogo. ${error.message}`;
    }
}

function crearTarjetaEntrada(tipo) {
    const presentacion = PRESENTACION_ENTRADAS[tipo.nombre] || {
        titulo: tipo.nombre,
        etiqueta: tipo.nombre.replaceAll('_', ' ').toUpperCase(),
        icono: '🎟',
        descripcion: tipo.descripcion || 'Entrada del festival.',
        ventajas: ['Acceso durante las fechas indicadas', 'Entrada personal con código']
    };

    const tarjeta = document.createElement('article');
    tarjeta.className = `ticket-card${presentacion.destacado ? ' ticket-card-featured' : ''}`;

    if (presentacion.destacado) {
        const cinta = document.createElement('div');
        cinta.className = 'ticket-ribbon';
        cinta.textContent = 'MÁS POPULAR';
        tarjeta.appendChild(cinta);
    }

    const linea = document.createElement('div');
    linea.className = 'ticket-topline';
    const icono = document.createElement('span');
    icono.className = 'ticket-icon';
    icono.setAttribute('aria-hidden', 'true');
    icono.textContent = presentacion.icono;
    const etiqueta = document.createElement('span');
    etiqueta.className = 'ticket-type';
    etiqueta.textContent = presentacion.etiqueta;
    linea.append(icono, etiqueta);

    const titulo = document.createElement('h3');
    titulo.textContent = presentacion.titulo;
    const descripcion = document.createElement('p');
    descripcion.className = 'ticket-description';
    descripcion.textContent = tipo.descripcion || presentacion.descripcion;

    const precio = document.createElement('div');
    precio.className = 'ticket-price';
    precio.append(document.createTextNode(`${Number(tipo.precio).toLocaleString('es-ES')} € `));
    const unidad = document.createElement('span');
    unidad.textContent = 'por entrada';
    precio.appendChild(unidad);

    const ventajas = document.createElement('ul');
    ventajas.className = 'ticket-benefits';
    presentacion.ventajas.forEach((texto) => {
        const item = document.createElement('li');
        item.textContent = texto;
        ventajas.appendChild(item);
    });

    const comprar = document.createElement('a');
    comprar.className = `btn ticket-button${presentacion.destacado ? ' btn-primary' : ' ticket-button-alt'}`;
    comprar.href = `comprar.html?idTipoEntrada=${encodeURIComponent(tipo.id)}`;
    comprar.textContent = 'Comprar';

    tarjeta.append(linea, titulo, descripcion, precio, ventajas, comprar);
    return tarjeta;
}

async function solicitarApiEntradas(ruta, opciones = {}) {
    let ultimoError;
    for (const base of API_ENTRADAS_CATALOGO) {
        let respuesta;
        try {
            respuesta = await fetch(`${base}${ruta}`, {
                ...opciones,
                headers: { 'Content-Type': 'application/json', ...opciones.headers }
            });
        } catch {
            continue;
        }

        let cuerpo;
        try {
            cuerpo = await respuesta.json();
        } catch {
            ultimoError = new Error('El servicio devolvió una respuesta no válida.');
            continue;
        }

        if (respuesta.status === 404 || respuesta.status === 405) continue;
        if (!respuesta.ok) {
            throw new Error(cuerpo.mensaje || cuerpo.detail || 'No se pudo consultar Entradas.');
        }
        return cuerpo;
    }
    throw ultimoError || new Error('No se pudo conectar con Entradas. Comprueba que el servicio esté iniciado en el puerto 8000.');
}
