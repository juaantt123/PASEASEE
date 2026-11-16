// --- GUARDIA DE SEGURIDAD ---
if (sessionStorage.getItem('tipoUsuario') !== 'administrador') {
    window.location.href = 'index.html';
}

const API_ENTRADAS = 'http://127.0.0.1:8000/api';
const API_ESCALETA = 'http://127.0.0.1:8002/api';
const API_ESPACIOS = 'http://127.0.0.1:8003/api';
const API_TIENDA = 'http://127.0.0.1:8004/api';

// --- CACHÉ DE DATOS LOCALES ---
let cache = { artistas: [], actuaciones: [], espacios: [], entradas: [], tienda: [] };

function cambiarPestana(idSeccion, botonGatillo) {
    document.querySelectorAll('.admin-section').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
    document.getElementById(idSeccion).classList.add('active');
    botonGatillo.classList.add('active');
}

function cerrarSesionAdmin() {
    sessionStorage.removeItem('tipoUsuario');
    sessionStorage.removeItem('subsonic-sesion');
    window.location.href = 'index.html';
}

// ==========================================
// FUNCIONES DE LECTURA (GET) Y RENDERIZADO
// ==========================================

function escaparTexto(valor) {
    const span = document.createElement('span');
    span.textContent = String(valor ?? '');
    return span.innerHTML;
}

async function cargarArtistas() {
    const tbody = document.getElementById('tabla-artistas');
    try {
        const [resArtistas, resActuaciones] = await Promise.all([
            fetch(`${API_ESCALETA}/escaleta/artistas`), fetch(`${API_ESCALETA}/escaleta`)
        ]);
        if (!resArtistas.ok || !resActuaciones.ok) throw new Error('No se pudieron cargar artistas y actuaciones');
        cache.artistas = await resArtistas.json();
        cache.actuaciones = await resActuaciones.json();
        const selector = document.getElementById('art-existente');
        const previo = selector.value;
        selector.replaceChildren(new Option('Nuevo artista', ''));
        for (const artista of cache.artistas) selector.add(new Option(artista.nombre, String(artista.id)));
        selector.value = previo;
        tbody.innerHTML = cache.artistas.flatMap(a => {
            const actuaciones = cache.actuaciones.filter(x => x.idArtista === a.id);
            return (actuaciones.length ? actuaciones : [null]).map(act => `
                <tr><td><strong>${escaparTexto(a.nombre)}</strong></td>
                <td>${escaparTexto(a.genero)}</td>
                <td>${act ? `${escaparTexto(act.fecha)} · ${escaparTexto(act.horaInicio.slice(0,5))}–${escaparTexto(act.horaFin.slice(0,5))}<br><small>${escaparTexto(act.nombreEspacio)} · ${escaparTexto(act.estado)}</small>` : 'Sin actuación programada'}</td>
                <td><button class="action-btn" onclick="editarActuacion(${a.id}, ${act ? act.id : 'null'})">✏️ ${act ? 'Editar actuación' : 'Programar'}</button>
                <button class="action-btn delete" onclick="eliminarRegistro('artista', ${a.id}, '${API_ESCALETA}/escaleta/artistas')">🗑️ Artista</button></td></tr>`);
        }).join('') || '<tr><td colspan="4">No hay artistas.</td></tr>';
    } catch (e) { tbody.innerHTML = '<tr><td colspan="4" style="color:#ff4444">Error al cargar artistas y actuaciones de Escaleta (8002)</td></tr>'; }
}

function actualizarEscenarios() {
    const selector = document.getElementById('art-escenario');
    const valor = selector.value;
    selector.replaceChildren(new Option('Selecciona un escenario', ''));
    for (const e of cache.espacios.filter(e => e.tipo === 'escenario' && ['activo', 'libre'].includes(e.estado))) {
        selector.add(new Option(e.nombre, String(e.id)));
    }
    selector.value = valor;
    selector.disabled = selector.options.length === 1;
}

function editarActuacion(idArtista, idActuacion) {
    const artista = cache.artistas.find(a => a.id === idArtista);
    const actuacion = cache.actuaciones.find(a => a.id === idActuacion);
    if (!artista) return;
    document.getElementById('art-id').value = artista.id;
    document.getElementById('art-existente').value = String(artista.id);
    document.getElementById('art-nombre').value = artista.nombre;
    document.getElementById('art-genero').value = artista.genero;
    document.getElementById('act-id').value = actuacion?.id || '';
    document.getElementById('art-fecha').value = actuacion?.fecha || '';
    document.getElementById('art-escenario').value = actuacion ? String(actuacion.idEspacio) : '';
    document.getElementById('art-horaInicio').value = actuacion?.horaInicio?.slice(0,5) || '';
    document.getElementById('art-horaFin').value = actuacion?.horaFin?.slice(0,5) || '';
    document.getElementById('btn-art-submit').textContent = actuacion ? 'Actualizar actuación' : 'Programar actuación';
    document.getElementById('btn-art-cancel').style.display = 'block';
    document.getElementById('art-mensaje').textContent = '';
}

async function cargarEspacios() {
    const tbody = document.getElementById('tabla-espacios');
    try {
        const res = await fetch(`${API_ESPACIOS}/espacios`);
        if (!res.ok) throw new Error();
        cache.espacios = await res.json();
        actualizarEscenarios();
        tbody.innerHTML = cache.espacios.map(e => `
            <tr>
                <td><strong>${e.nombre}</strong></td>
                <td>${e.tipo}<br><small style="color:#888;">${e.ubicacion}</small></td>
                <td>${e.capacidad} pax</td>
                <td><span class="status-badge">${e.estado}</span></td>
                <td>
                    <button class="action-btn" onclick="prepararEdicion('espacio', ${e.id})">✏️</button>
                    <button class="action-btn delete" onclick="eliminarRegistro('espacio', ${e.id}, '${API_ESPACIOS}/espacios')">🗑️</button>
                </td>
            </tr>
        `).join('') || `<tr><td colspan="5" style="text-align: center;">No hay espacios configurados.</td></tr>`;
    } catch (e) { tbody.innerHTML = `<tr><td colspan="5" style="color: #ff4444;">Error de conexión con API Espacios (8003)</td></tr>`; }
}

async function cargarEntradas() {
    const tbody = document.getElementById('tabla-entradas');
    try {
        const res = await fetch(`${API_ENTRADAS}/entradas`);
        if (!res.ok) throw new Error();
        cache.entradas = await res.json();
        tbody.innerHTML = cache.entradas.map(e => `
            <tr>
                <td><strong>${e.nombre}</strong><br><small style="color:#888">${e.descripcion}</small></td>
                <td>${e.precio} €</td>
                <td>${e.stockDisponible} / ${e.stockTotal}</td>
                <td><span class="status-badge">${e.estado}</span></td>
                <td>
                    <button class="action-btn" onclick="prepararEdicion('entrada', ${e.id})">✏️</button>
                    <button class="action-btn delete" onclick="eliminarRegistro('entrada', ${e.id}, '${API_ENTRADAS}/entradas')">🗑️</button>
                </td>
            </tr>
        `).join('') || `<tr><td colspan="5" style="text-align: center;">No hay pases configurados.</td></tr>`;
    } catch (e) { tbody.innerHTML = `<tr><td colspan="5" style="color: #ff4444;">Error de conexión con API Entradas (8000)</td></tr>`; }
}

async function cargarTienda() {
    const tbody = document.getElementById('tabla-tienda');
    try {
        const res = await fetch(`${API_TIENDA}/merchandising`);
        if (!res.ok) throw new Error();
        cache.tienda = await res.json();
        tbody.innerHTML = cache.tienda.map(p => `
            <tr>
                <td><strong>${p.nombre}</strong></td>
                <td style="text-transform: capitalize;">${p.categoria}</td>
                <td>${p.precio} €</td>
                <td>${p.stock} uds</td>
                <td>
                    <button class="action-btn" onclick="prepararEdicion('producto', ${p.id})">✏️</button>
                    <button class="action-btn delete" onclick="eliminarRegistro('producto', ${p.id}, '${API_TIENDA}/merchandising')">🗑️</button>
                </td>
            </tr>
        `).join('') || `<tr><td colspan="5" style="text-align: center;">No hay productos.</td></tr>`;
    } catch (e) { tbody.innerHTML = `<tr><td colspan="5" style="color: #ff4444;">Error de conexión con API Tienda (8004)</td></tr>`; }
}

document.addEventListener('DOMContentLoaded', () => {
    cargarArtistas(); cargarEspacios(); cargarEntradas(); cargarTienda();
});

// ==========================================
// MÉTODOS AUXILIARES: ELIMINAR Y PREPARAR EDICIÓN
// ==========================================

async function eliminarRegistro(tipo, id, urlBase) {
    if (!confirm(`¿Seguro que quieres eliminar este ${tipo}?`)) return;
    try {
        const res = await fetch(`${urlBase}/${id}`, { method: 'DELETE' });
        if (res.ok) {
            if (tipo === 'artista') cargarArtistas();
            if (tipo === 'espacio') cargarEspacios();
            if (tipo === 'entrada') cargarEntradas();
            if (tipo === 'producto') cargarTienda();
        } else {
            const err = await res.json();
            alert(`No se pudo eliminar: ${err.mensaje || 'Restricción de base de datos'}`);
        }
    } catch (e) { alert('Error de red al intentar eliminar.'); }
}

function prepararEdicion(tipo, id) {
    if (tipo === 'artista') {
        editarActuacion(id, null);
    } else if (tipo === 'espacio') {
        const item = cache.espacios.find(x => x.id === id);
        document.getElementById('esp-id').value = item.id;
        document.getElementById('esp-nombre').value = item.nombre;
        document.getElementById('esp-tipo').value = item.tipo;
        document.getElementById('esp-estado').value = item.estado;
        document.getElementById('esp-ubicacion').value = item.ubicacion;
        document.getElementById('esp-capacidad').value = item.capacidad;
        document.getElementById('btn-esp-submit').innerText = 'Actualizar Espacio';
        document.getElementById('btn-esp-cancel').style.display = 'block';
    } else if (tipo === 'entrada') {
        const item = cache.entradas.find(x => x.id === id);
        document.getElementById('ent-id').value = item.id;
        document.getElementById('ent-nombre').value = item.nombre;
        document.getElementById('ent-desc').value = item.descripcion;
        document.getElementById('ent-precio').value = item.precio;
        document.getElementById('ent-cantidad').value = item.stockTotal;
        document.getElementById('btn-ent-submit').innerText = 'Actualizar Pase';
        document.getElementById('btn-ent-cancel').style.display = 'block';
    } else if (tipo === 'producto') {
        const item = cache.tienda.find(x => x.id === id);
        document.getElementById('prod-id').value = item.id;
        document.getElementById('prod-nombre').value = item.nombre;
        document.getElementById('prod-categoria').value = item.categoria;
        document.getElementById('prod-precio').value = item.precio;
        document.getElementById('prod-stock').value = item.stock;
        document.getElementById('btn-prod-submit').innerText = 'Actualizar Producto';
        document.getElementById('btn-prod-cancel').style.display = 'block';
    }
}

function cancelarEdicion(tipo) {
    if (tipo === 'artista') {
        document.getElementById('form-artista').reset();
        document.getElementById('art-id').value = '';
        document.getElementById('act-id').value = '';
        document.getElementById('art-mensaje').textContent = '';
        document.getElementById('btn-art-submit').innerText = 'Guardar Artista';
        document.getElementById('btn-art-cancel').style.display = 'none';
    } else if (tipo === 'espacio') {
        document.getElementById('form-espacio').reset();
        document.getElementById('esp-id').value = '';
        document.getElementById('btn-esp-submit').innerText = 'Registrar Espacio';
        document.getElementById('btn-esp-cancel').style.display = 'none';
    } else if (tipo === 'entrada') {
        document.getElementById('form-entrada').reset();
        document.getElementById('ent-id').value = '';
        document.getElementById('btn-ent-submit').innerText = 'Guardar Pase';
        document.getElementById('btn-ent-cancel').style.display = 'none';
    } else if (tipo === 'producto') {
        document.getElementById('form-producto').reset();
        document.getElementById('prod-id').value = '';
        document.getElementById('btn-prod-submit').innerText = 'Añadir Producto';
        document.getElementById('btn-prod-cancel').style.display = 'none';
    }
}

// ==========================================
// FUNCIONES DE ESCRITURA (POST / PUT)
// ==========================================

async function enviarFormulario(urlBase, id, datos, recargarFunc, cancelarFunc) {
    const method = id ? 'PUT' : 'POST';
    const url = id ? `${urlBase}/${id}` : urlBase;
    
    try {
        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(datos)
        });
        if (res.ok) { cancelarFunc(); recargarFunc(); }
        else { const err = await res.json(); alert(`Error: ${err.mensaje || JSON.stringify(err)}`); }
    } catch (error) { alert(`Error conectando con la API en: ${url}`); }
}

document.getElementById('art-existente').addEventListener('change', event => {
    const id = Number(event.target.value);
    if (id) editarActuacion(id, null);
    else cancelarEdicion('artista');
});

async function peticionEscaleta(url, method, datos) {
    const res = await fetch(url, { method, headers: {'Content-Type': 'application/json'}, body: JSON.stringify(datos) });
    if (!res.ok) {
        let detalle = `Error ${res.status}`;
        try { const error = await res.json(); detalle = error.mensaje || error.detail || detalle; } catch {}
        throw new Error(typeof detalle === 'string' ? detalle : 'Datos no válidos');
    }
    return res.json();
}

document.getElementById('form-artista').addEventListener('submit', async e => {
    e.preventDefault();
    const form = e.currentTarget;
    const boton = document.getElementById('btn-art-submit');
    const mensaje = document.getElementById('art-mensaje');
    let artistaId = document.getElementById('art-id').value;
    const actuacionId = document.getElementById('act-id').value;
    const anterior = cache.actuaciones.find(a => String(a.id) === actuacionId);
    const datosArtista = { nombre: document.getElementById('art-nombre').value.trim(), genero: document.getElementById('art-genero').value.trim() };
    const datosActuacion = {
        idEspacio: Number(document.getElementById('art-escenario').value),
        fecha: document.getElementById('art-fecha').value,
        horaInicio: document.getElementById('art-horaInicio').value,
        horaFin: document.getElementById('art-horaFin').value,
        estado: anterior?.estado || 'programada'
    };
    if (!form.reportValidity()) return;
    if (datosActuacion.horaFin <= datosActuacion.horaInicio) {
        mensaje.textContent = 'La hora de fin debe ser posterior a la hora de inicio.';
        return;
    }
    boton.disabled = true;
    mensaje.textContent = 'Guardando…';
    try {
        const artista = await peticionEscaleta(`${API_ESCALETA}/escaleta/artistas${artistaId ? '/' + artistaId : ''}`, artistaId ? 'PUT' : 'POST', datosArtista);
        artistaId = String(artista.id);
        document.getElementById('art-id').value = artistaId;
        datosActuacion.idArtista = artista.id;
        await peticionEscaleta(`${API_ESCALETA}/escaleta${actuacionId ? '/' + actuacionId : ''}`, actuacionId ? 'PUT' : 'POST', datosActuacion);
        cancelarEdicion('artista');
        await cargarArtistas();
        mensaje.textContent = 'Artista y actuación guardados. Ya puedes ver la programación en Escaleta.';
    } catch (error) {
        mensaje.textContent = `${artistaId ? 'El artista está guardado. La actuación no se ha guardado: ' : 'No se ha guardado el artista: '}${error.message}`;
        await cargarArtistas();
        if (artistaId) document.getElementById('art-existente').value = artistaId;
    } finally { boton.disabled = false; }
});

document.getElementById('form-espacio').addEventListener('submit', (e) => {
    e.preventDefault();
    const id = document.getElementById('esp-id').value;
    const existente = cache.espacios.find(espacio => String(espacio.id) === id);
    const datos = {
        nombre: document.getElementById('esp-nombre').value, tipo: document.getElementById('esp-tipo').value,
        ubicacion: document.getElementById('esp-ubicacion').value, capacidad: parseInt(document.getElementById('esp-capacidad').value),
        estado: document.getElementById('esp-estado').value,
        ...(existente ? { tamano: existente.tamano, descripcion: existente.descripcion } : {})
    };
    enviarFormulario(`${API_ESPACIOS}/espacios`, id, datos, cargarEspacios, () => cancelarEdicion('espacio'));
});

document.getElementById('form-entrada').addEventListener('submit', (e) => {
    e.preventDefault();
    const id = document.getElementById('ent-id').value;
    const datos = {
        nombre: document.getElementById('ent-nombre').value, descripcion: document.getElementById('ent-desc').value,
        precio: parseFloat(document.getElementById('ent-precio').value), stockTotal: parseInt(document.getElementById('ent-cantidad').value),
        fechaInicioValidez: "2027-07-15", fechaFinValidez: "2027-07-18"
    };
    enviarFormulario(`${API_ENTRADAS}/entradas`, id, datos, cargarEntradas, () => cancelarEdicion('entrada'));
});

document.getElementById('form-producto').addEventListener('submit', (e) => {
    e.preventDefault();
    const id = document.getElementById('prod-id').value;
    const datos = {
        nombre: document.getElementById('prod-nombre').value, categoria: document.getElementById('prod-categoria').value,
        precio: parseFloat(document.getElementById('prod-precio').value), stock: parseInt(document.getElementById('prod-stock').value)
    };
    enviarFormulario(`${API_TIENDA}/merchandising`, id, datos, cargarTienda, () => cancelarEdicion('producto'));
});
