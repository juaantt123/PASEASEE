// --- GUARDIA DE SEGURIDAD ---
if (sessionStorage.getItem('tipoUsuario') !== 'administrador') {
    window.location.href = 'index.html';
}

const API_ENTRADAS = 'http://127.0.0.1:8000/api';
const API_ESCALETA = 'http://127.0.0.1:8002/api';
const API_ESPACIOS = 'http://127.0.0.1:8003/api';
const API_TIENDA = 'http://127.0.0.1:8004/api';

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
// LECTURA DE DATOS Y RENDERIZADO DE TABLAS
// ==========================================

async function cargarArtistas() {
    const tbody = document.getElementById('tabla-artistas');
    const selectExistente = document.getElementById('art-existente');
    try {
        const resArt = await fetch(`${API_ESCALETA}/escaleta/artistas`);
        cache.artistas = await resArt.json();
        
        const resAct = await fetch(`${API_ESCALETA}/escaleta`);
        cache.actuaciones = await resAct.json();

        // Rellenar selector de edición
        selectExistente.innerHTML = '<option value="">-- Crear nuevo artista --</option>' + 
            cache.artistas.map(a => `<option value="${a.id}">${a.nombre}</option>`).join('');

        // Montar tabla cruzando Artistas y Actuaciones
        tbody.innerHTML = cache.artistas.map(artista => {
            const acts = cache.actuaciones.filter(a => a.idArtista === artista.id);
            if (acts.length === 0) {
                return `<tr>
                    <td><strong>${artista.nombre}</strong></td><td>${artista.genero}</td>
                    <td><small style="color:#888;">Sin programar</small></td>
                    <td>
                        <button class="action-btn" onclick="editarActuacion(${artista.id}, null)">✏️</button>
                        <button class="action-btn delete" onclick="eliminarRegistro('artista', ${artista.id}, '${API_ESCALETA}/escaleta/artistas')">🗑️</button>
                    </td>
                </tr>`;
            }
            return acts.map(act => `<tr>
                <td><strong>${artista.nombre}</strong></td><td>${artista.genero}</td>
                <td><small style="color:#c2ff00;">${act.fecha} | ${act.horaInicio.slice(0,5)} - ${act.horaFin.slice(0,5)}</small><br><small style="color:#888;">${act.nombreEspacio}</small></td>
                <td>
                    <button class="action-btn" onclick="editarActuacion(${artista.id}, ${act.id})">✏️</button>
                    <button class="action-btn delete" onclick="eliminarRegistro('actuacion', ${act.id}, '${API_ESCALETA}/escaleta')">🗑️</button>
                </td>
            </tr>`).join('');
        }).join('') || `<tr><td colspan="4" style="text-align: center;">No hay artistas registrados.</td></tr>`;
    } catch (e) { tbody.innerHTML = `<tr><td colspan="4" style="color: #ff4444;">Error conectando con API Escaleta (8002)</td></tr>`; }
}

function actualizarEscenarios() {
    const selector = document.getElementById('art-escenario');
    const valor = selector.value;
    selector.replaceChildren(new Option('Selecciona un escenario...', ''));
    cache.espacios.filter(e => e.tipo.toLowerCase() === 'escenario').forEach(e => {
        selector.add(new Option(e.nombre, String(e.id)));
    });
    selector.value = valor;
}

async function cargarEspacios() {
    const tbody = document.getElementById('tabla-espacios');
    try {
        const res = await fetch(`${API_ESPACIOS}/espacios`);
        cache.espacios = await res.json();
        actualizarEscenarios(); // Recarga el desplegable de escenarios en la pestaña Artistas
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
    } catch (e) { tbody.innerHTML = `<tr><td colspan="5" style="color: #ff4444;">Error conectando con API Espacios (8003)</td></tr>`; }
}

async function cargarEntradas() {
    const tbody = document.getElementById('tabla-entradas');
    try {
        const res = await fetch(`${API_ENTRADAS}/entradas`);
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
    } catch (e) { tbody.innerHTML = `<tr><td colspan="5" style="color: #ff4444;">Error conectando con API Entradas (8000)</td></tr>`; }
}

async function cargarTienda() {
    const tbody = document.getElementById('tabla-tienda');
    try {
        const res = await fetch(`${API_TIENDA}/merchandising`);
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
    } catch (e) { tbody.innerHTML = `<tr><td colspan="5" style="color: #ff4444;">Error conectando con API Tienda (8004)</td></tr>`; }
}

document.addEventListener('DOMContentLoaded', () => {
    cargarArtistas(); cargarEspacios(); cargarEntradas(); cargarTienda();
});

// ==========================================
// ACCIONES (ELIMINAR Y EDITAR)
// ==========================================

async function eliminarRegistro(tipo, id, urlBase) {
    if (!confirm(`¿Seguro que quieres eliminar este elemento?`)) return;
    try {
        const res = await fetch(`${urlBase}/${id}`, { method: 'DELETE' });
        if (res.ok) {
            if (tipo === 'artista' || tipo === 'actuacion') cargarArtistas();
            if (tipo === 'espacio') cargarEspacios();
            if (tipo === 'entrada') cargarEntradas();
            if (tipo === 'producto') cargarTienda();
        } else {
            const err = await res.json();
            alert(`No se pudo eliminar: ${err.mensaje || 'Error en base de datos'}`);
        }
    } catch (e) { alert('Error de red al intentar eliminar.'); }
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
    document.getElementById('btn-art-submit').textContent = 'Guardar Cambios';
    document.getElementById('btn-art-cancel').style.display = 'block';
    document.getElementById('art-mensaje').textContent = '';
}

document.getElementById('art-existente').addEventListener('change', event => {
    const id = Number(event.target.value);
    if (id) editarActuacion(id, null);
    else cancelarEdicion('artista');
});

function prepararEdicion(tipo, id) {
    if (tipo === 'espacio') {
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
    document.getElementById(`form-${tipo}`).reset();
    document.getElementById(tipo === 'producto' ? 'prod-id' : `${tipo.substring(0,3)}-id`).value = '';
    
    if (tipo === 'artista') {
        document.getElementById('act-id').value = '';
        document.getElementById('art-mensaje').textContent = '';
        document.getElementById('btn-art-submit').innerText = 'Guardar Artista';
        document.getElementById('btn-art-cancel').style.display = 'none';
    } else {
        document.getElementById(`btn-${tipo === 'producto' ? 'prod' : tipo.substring(0,3)}-submit`).innerText = 'Guardar';
        document.getElementById(`btn-${tipo === 'producto' ? 'prod' : tipo.substring(0,3)}-cancel`).style.display = 'none';
    }
}

// ==========================================
// ENVÍO DE FORMULARIOS (POST/PUT)
// ==========================================

async function enviarFormulario(urlBase, id, datos, recargarFunc, cancelarFunc) {
    try {
        const res = await fetch(id ? `${urlBase}/${id}` : urlBase, {
            method: id ? 'PUT' : 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(datos)
        });
        if (res.ok) { cancelarFunc(); recargarFunc(); }
        else { const err = await res.json(); alert(`Error: ${err.mensaje || JSON.stringify(err)}`); }
    } catch (error) { alert('Error de conexión con la API.'); }
}

async function peticionEscaleta(url, method, datos) {
    const res = await fetch(url, { method, headers: {'Content-Type': 'application/json'}, body: JSON.stringify(datos) });
    if (!res.ok) {
        let detalle = `Error ${res.status}`;
        try { const error = await res.json(); detalle = error.mensaje || detalle; } catch {}
        throw new Error(detalle);
    }
    return res.json();
}

document.getElementById('form-artista').addEventListener('submit', async e => {
    e.preventDefault();
    const boton = document.getElementById('btn-art-submit');
    const mensaje = document.getElementById('art-mensaje');
    let artistaId = document.getElementById('art-id').value;
    const actuacionId = document.getElementById('act-id').value;
    
    const datosArtista = { nombre: document.getElementById('art-nombre').value.trim(), genero: document.getElementById('art-genero').value.trim() };
    const idEscenario = document.getElementById('art-escenario').value;
    
    boton.disabled = true;
    mensaje.style.color = '#fff';
    mensaje.textContent = 'Guardando...';

    try {
        // 1. Guardar Artista
        const artista = await peticionEscaleta(`${API_ESCALETA}/escaleta/artistas${artistaId ? '/'+artistaId : ''}`, artistaId ? 'PUT' : 'POST', datosArtista);
        artistaId = String(artista.id);
        
        // 2. Guardar Actuación (Solo si se han rellenado los campos de fecha y escenario)
        if (idEscenario && document.getElementById('art-fecha').value) {
            const hInicio = document.getElementById('art-horaInicio').value;
            const hFin = document.getElementById('art-horaFin').value;
            
            if (hFin <= hInicio) throw new Error("La hora de fin debe ser posterior a la de inicio.");
            
            const datosActuacion = {
                idArtista: artista.id, idEspacio: Number(idEscenario),
                fecha: document.getElementById('art-fecha').value,
                horaInicio: hInicio.length === 5 ? hInicio + ":00" : hInicio,
                horaFin: hFin.length === 5 ? hFin + ":00" : hFin,
                estado: "programada"
            };
            await peticionEscaleta(`${API_ESCALETA}/escaleta${actuacionId ? '/'+actuacionId : ''}`, actuacionId ? 'PUT' : 'POST', datosActuacion);
        }

        cancelarEdicion('artista');
        await cargarArtistas();
        mensaje.style.color = '#c2ff00';
        mensaje.textContent = 'Guardado correctamente.';
        setTimeout(() => mensaje.textContent = '', 3000);
    } catch (error) {
        mensaje.style.color = '#ff4444';
        mensaje.textContent = `Error: ${error.message}`;
        await cargarArtistas();
    } finally {
        boton.disabled = false;
    }
});

document.getElementById('form-espacio').addEventListener('submit', (e) => {
    e.preventDefault();
    const id = document.getElementById('esp-id').value;
    const datos = {
        nombre: document.getElementById('esp-nombre').value, tipo: document.getElementById('esp-tipo').value,
        ubicacion: document.getElementById('esp-ubicacion').value, capacidad: parseInt(document.getElementById('esp-capacidad').value),
        estado: document.getElementById('esp-estado').value
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