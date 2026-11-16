const API_ESPACIOS = 'http://127.0.0.1:8003/api';
const API_ADMIN_ESCALETA = 'http://127.0.0.1:8002/api';

let artistasAdmin = [];
let actuacionesAdmin = [];
let espaciosAdmin = [];

async function adminRequest(url, options) {
    const response = await fetch(url, options);
    if (!response.ok) {
        let detail = `Error ${response.status}`;
        try {
            const body = await response.json();
            detail = body.mensaje || body.detail || detail;
        } catch (error) {
            // La respuesta puede no incluir un cuerpo JSON.
        }
        throw new Error(detail);
    }
    if (response.status === 204) {
        return null;
    }
    return response.json();
}

function escaparHTML(value) {
    return String(value ?? '').replace(/[&<>"']/g, character => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    })[character]);
}

function mostrarMensaje(elementId, mensaje, success = false) {
    const element = document.getElementById(elementId);
    element.textContent = mensaje;
    element.classList.toggle('is-success', success);
}

function etiquetaTipo(tipo) {
    const etiquetas = {
        escenario: 'Escenario',
        comida: 'Comida',
        restauracion: 'Comida',
        tienda_ropa: 'Tienda de ropa',
        merchandising: 'Tienda de ropa',
        tatuador: 'Tatuador',
        servicios: 'Servicios',
        descanso: 'Descanso',
        otros: 'Otros'
    };
    return etiquetas[tipo] || tipo;
}

function etiquetaEstado(estado) {
    const etiquetas = {
        activo: 'Libre',
        libre: 'Libre',
        cerrado: 'Ocupado',
        ocupado: 'Ocupado',
        mantenimiento: 'En mantenimiento'
    };
    return etiquetas[estado] || estado;
}

function actuacionesDe(artistaId) {
    return actuacionesAdmin.filter(actuacion => actuacion.idArtista === artistaId);
}

function renderizarArtistas() {
    const list = document.getElementById('artists-list');
    if (!artistasAdmin.length) {
        list.innerHTML = '<p class="dashboard-hint">Todavía no hay artistas registrados.</p>';
        return;
    }

    list.innerHTML = artistasAdmin.map(artista => {
        const actuaciones = actuacionesDe(artista.id);
        const detalles = actuaciones.length
            ? actuaciones.map(actuacion => `
                <div class="admin-schedule">
                    <p>${escaparHTML(actuacion.nombreEspacio)} · ${escaparHTML(actuacion.fecha)} · ${escaparHTML(actuacion.horaInicio.slice(0, 5))}–${escaparHTML(actuacion.horaFin.slice(0, 5))}</p>
                    <button class="admin-action" type="button" data-edit-artist="${artista.id}" data-act-id="${actuacion.id}">Editar</button>
                </div>
            `).join('')
            : '<p class="dashboard-hint">Sin actuaciones programadas</p>';

        return `
            <article class="admin-item">
                <div class="admin-item-heading">
                    <div>
                        <h4>${escaparHTML(artista.nombre)}</h4>
                        <span class="admin-item-meta">ID ${artista.id} · ${actuaciones.length} ${actuaciones.length === 1 ? 'actuación' : 'actuaciones'}</span>
                    </div>
                    <div class="admin-item-actions">
                        ${actuaciones.length === 0 ? `<button class="admin-action" type="button" data-edit-artist="${artista.id}">Editar</button>` : ''}
                        <button class="admin-action is-danger" type="button" data-delete-artist="${artista.id}">Eliminar</button>
                    </div>
                </div>
                ${detalles}
            </article>
        `;
    }).join('');
}

function renderizarEspacios() {
    const list = document.getElementById('spaces-list');
    if (!espaciosAdmin.length) {
        list.innerHTML = '<p class="dashboard-hint">Todavía no hay espacios registrados.</p>';
        return;
    }

    list.innerHTML = espaciosAdmin.map(espacio => `
        <article class="admin-item">
            <div class="admin-item-heading">
                <div>
                    <h4>${escaparHTML(espacio.nombre)}</h4>
                    <span class="admin-item-meta">${escaparHTML(etiquetaTipo(espacio.tipo))} · ${escaparHTML(espacio.ubicacion)} · ${escaparHTML(espacio.tamano)} m²</span>
                </div>
                <span class="admin-state">${escaparHTML(etiquetaEstado(espacio.estado))}</span>
            </div>
            ${espacio.descripcion ? `<p class="admin-description">${escaparHTML(espacio.descripcion)}</p>` : ''}
            <div class="admin-item-actions">
                <button class="admin-action" type="button" data-edit-space="${espacio.id}">Editar</button>
                <button class="admin-action is-danger" type="button" data-delete-space="${espacio.id}">Eliminar</button>
            </div>
        </article>
    `).join('');
}

function actualizarEscenarios() {
    const select = document.getElementById('artist-stage');
    const escenarios = espaciosAdmin.filter(espacio =>
        espacio.tipo === 'escenario' && ['activo', 'libre'].includes(espacio.estado)
    );
    select.innerHTML = '<option value="">Selecciona un escenario</option>' +
        escenarios.map(espacio => `<option value="${espacio.id}">${escaparHTML(espacio.nombre)}</option>`).join('');
    select.disabled = escenarios.length === 0;
    if (!escenarios.length) {
        select.innerHTML = '<option value="">No hay escenarios disponibles</option>';
    }
}

async function cargarArtistas() {
    const [artistas, actuaciones] = await Promise.all([
        adminRequest(`${API_ADMIN_ESCALETA}/escaleta/artistas`),
        adminRequest(`${API_ADMIN_ESCALETA}/escaleta`)
    ]);
    artistasAdmin = artistas;
    actuacionesAdmin = actuaciones;
    renderizarArtistas();
}

async function cargarEspacios() {
    espaciosAdmin = await adminRequest(`${API_ESPACIOS}/espacios`);
    renderizarEspacios();
    actualizarEscenarios();
}

function limpiarFormularioArtista() {
    document.getElementById('artist-form').reset();
    document.getElementById('artist-id').value = '';
    document.getElementById('performance-id').value = '';
    document.getElementById('artist-submit').textContent = 'Añadir artista';
    document.getElementById('artist-cancel').hidden = true;
    mostrarMensaje('artist-message', '');
}

function limpiarFormularioEspacio() {
    document.getElementById('space-form').reset();
    document.getElementById('space-id').value = '';
    document.getElementById('space-submit').textContent = 'Añadir espacio';
    document.getElementById('space-cancel').hidden = true;
    mostrarMensaje('space-message', '');
}

function editarArtista(artistId, performanceId) {
    const artista = artistasAdmin.find(item => item.id === artistId);
    if (!artista) {
        return;
    }

    const actuacion = actuacionesAdmin.find(item => item.id === performanceId);
    document.getElementById('artist-id').value = artista.id;
    document.getElementById('performance-id').value = actuacion ? actuacion.id : '';
    document.getElementById('artist-name').value = artista.nombre;
    document.getElementById('artist-stage').value = actuacion ? actuacion.idEspacio : '';
    document.getElementById('artist-date').value = actuacion ? actuacion.fecha : '';
    document.getElementById('artist-start').value = actuacion ? actuacion.horaInicio.slice(0, 5) : '';
    document.getElementById('artist-end').value = actuacion ? actuacion.horaFin.slice(0, 5) : '';
    document.getElementById('artist-submit').textContent = 'Guardar artista y horario';
    document.getElementById('artist-cancel').hidden = false;
    mostrarMensaje('artist-message', '');
    document.getElementById('artist-form').scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function editarEspacio(spaceId) {
    const espacio = espaciosAdmin.find(item => item.id === spaceId);
    if (!espacio) {
        return;
    }

    const tipo = {
        restauracion: 'comida',
        merchandising: 'tienda_ropa'
    }[espacio.tipo] || espacio.tipo;
    const estado = {
        activo: 'libre',
        cerrado: 'ocupado'
    }[espacio.estado] || espacio.estado;
    document.getElementById('space-id').value = espacio.id;
    document.getElementById('space-name').value = espacio.nombre;
    document.getElementById('space-type').value = tipo;
    document.getElementById('space-size').value = espacio.tamano || '';
    document.getElementById('space-location').value = espacio.ubicacion;
    document.getElementById('space-description').value = espacio.descripcion || '';
    document.getElementById('space-state').value = estado;
    document.getElementById('space-submit').textContent = 'Guardar espacio';
    document.getElementById('space-cancel').hidden = false;
    mostrarMensaje('space-message', '');
    document.getElementById('space-form').scrollIntoView({ behavior: 'smooth', block: 'center' });
}

async function guardarArtista(event) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.reportValidity()) {
        return;
    }

    const artistId = document.getElementById('artist-id').value;
    const performanceId = document.getElementById('performance-id').value;
    const artistaActual = artistasAdmin.find(item => item.id === Number(artistId));
    const actuacionActual = actuacionesAdmin.find(item => item.id === Number(performanceId));
    const datosArtista = {
        nombre: document.getElementById('artist-name').value.trim(),
        genero: artistaActual?.genero || 'sin especificar'
    };
    const datosActuacion = {
        idArtista: Number(artistId) || undefined,
        idEspacio: Number(document.getElementById('artist-stage').value),
        fecha: document.getElementById('artist-date').value,
        horaInicio: document.getElementById('artist-start').value,
        horaFin: document.getElementById('artist-end').value,
        estado: actuacionActual?.estado || 'programada'
    };
    let artistaGuardado = false;

    try {
        const artista = await adminRequest(
            artistId ? `${API_ADMIN_ESCALETA}/escaleta/artistas/${artistId}` : `${API_ADMIN_ESCALETA}/escaleta/artistas`,
            {
                method: artistId ? 'PUT' : 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(datosArtista)
            }
        );
        artistaGuardado = true;
        datosActuacion.idArtista = artista.id;

        await adminRequest(
            performanceId
                ? `${API_ADMIN_ESCALETA}/escaleta/${performanceId}`
                : `${API_ADMIN_ESCALETA}/escaleta`,
            {
                method: performanceId ? 'PUT' : 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(datosActuacion)
            }
        );

        limpiarFormularioArtista();
        mostrarMensaje('artist-message', 'Artista y actuación guardados correctamente.', true);
    } catch (error) {
        const prefijo = artistaGuardado ? 'El artista se guardó, pero no se pudo guardar la actuación: ' : '';
        mostrarMensaje('artist-message', `${prefijo}${error.message}`);
        if (artistaGuardado) {
            cargarArtistas().catch(refreshError =>
                mostrarMensaje('artist-message', `${prefijo}${error.message}. No se pudo actualizar la lista: ${refreshError.message}`)
            );
        }
        return;
    }

    cargarArtistas().catch(error =>
        mostrarMensaje('artist-message', `Guardado, pero no se pudo actualizar la lista: ${error.message}`)
    );
}

async function guardarEspacio(event) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.reportValidity()) {
        return;
    }

    const spaceId = document.getElementById('space-id').value;
    const espacioActual = espaciosAdmin.find(item => item.id === Number(spaceId));
    const datos = {
        nombre: document.getElementById('space-name').value.trim(),
        tipo: document.getElementById('space-type').value,
        ubicacion: document.getElementById('space-location').value.trim(),
        tamano: Number(document.getElementById('space-size').value),
        capacidad: espacioActual?.capacidad || 1,
        descripcion: document.getElementById('space-description').value.trim(),
        estado: document.getElementById('space-state').value
    };

    try {
        await adminRequest(
            spaceId ? `${API_ESPACIOS}/espacios/${spaceId}` : `${API_ESPACIOS}/espacios`,
            {
                method: spaceId ? 'PUT' : 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(datos)
            }
        );
        limpiarFormularioEspacio();
        mostrarMensaje('space-message', 'Espacio guardado correctamente.', true);
    } catch (error) {
        mostrarMensaje('space-message', error.message);
        return;
    }

    cargarEspacios().catch(error =>
        mostrarMensaje('space-message', `Guardado, pero no se pudo actualizar la lista: ${error.message}`)
    );
}

async function eliminarArtista(artistId) {
    const artista = artistasAdmin.find(item => item.id === artistId);
    if (!artista) {
        return;
    }
    const actuaciones = actuacionesDe(artistId);
    const aviso = actuaciones.length
        ? `Se eliminará "${artista.nombre}" y sus ${actuaciones.length} actuaciones. ¿Continuar?`
        : `¿Eliminar al artista "${artista.nombre}"?`;
    if (!window.confirm(aviso)) {
        return;
    }

    try {
        for (const actuacion of actuaciones) {
            await adminRequest(`${API_ADMIN_ESCALETA}/escaleta/${actuacion.id}`, { method: 'DELETE' });
        }
        await adminRequest(`${API_ADMIN_ESCALETA}/escaleta/artistas/${artistId}`, { method: 'DELETE' });
        mostrarMensaje('artist-message', 'Artista eliminado.', true);
    } catch (error) {
        mostrarMensaje('artist-message', `No se pudo completar la eliminación: ${error.message}`);
        cargarArtistas().catch(refreshError =>
            mostrarMensaje('artist-message', `No se pudo completar la eliminación: ${error.message}. Tampoco se pudo actualizar la lista: ${refreshError.message}`)
        );
        return;
    }
    cargarArtistas().catch(error =>
        mostrarMensaje('artist-message', `Artista eliminado, pero no se pudo actualizar la lista: ${error.message}`)
    );
}

async function eliminarEspacio(spaceId) {
    const espacio = espaciosAdmin.find(item => item.id === spaceId);
    if (!espacio || !window.confirm(`¿Eliminar el espacio "${espacio.nombre}"?`)) {
        return;
    }

    try {
        await adminRequest(`${API_ESPACIOS}/espacios/${spaceId}`, { method: 'DELETE' });
        mostrarMensaje('space-message', 'Espacio eliminado.', true);
    } catch (error) {
        mostrarMensaje('space-message', error.message);
        return;
    }
    cargarEspacios().catch(error =>
        mostrarMensaje('space-message', `Espacio eliminado, pero no se pudo actualizar la lista: ${error.message}`)
    );
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('artist-form').addEventListener('submit', guardarArtista);
    document.getElementById('space-form').addEventListener('submit', guardarEspacio);
    document.getElementById('artist-cancel').addEventListener('click', limpiarFormularioArtista);
    document.getElementById('space-cancel').addEventListener('click', limpiarFormularioEspacio);
    document.getElementById('artists-refresh').addEventListener('click', () => {
        cargarArtistas().catch(error => mostrarMensaje('artist-message', error.message));
    });
    document.getElementById('spaces-refresh').addEventListener('click', () => {
        cargarEspacios().catch(error => mostrarMensaje('space-message', error.message));
    });

    document.getElementById('artists-list').addEventListener('click', event => {
        const editButton = event.target.closest('[data-edit-artist]');
        if (editButton) {
            editarArtista(Number(editButton.dataset.editArtist), Number(editButton.dataset.actId));
            return;
        }
        const deleteButton = event.target.closest('[data-delete-artist]');
        if (deleteButton) {
            eliminarArtista(Number(deleteButton.dataset.deleteArtist));
        }
    });

    document.getElementById('spaces-list').addEventListener('click', event => {
        const editButton = event.target.closest('[data-edit-space]');
        if (editButton) {
            editarEspacio(Number(editButton.dataset.editSpace));
            return;
        }
        const deleteButton = event.target.closest('[data-delete-space]');
        if (deleteButton) {
            eliminarEspacio(Number(deleteButton.dataset.deleteSpace));
        }
    });

    cargarArtistas().catch(error => {
        document.getElementById('artists-list').innerHTML = `<p class="admin-error">${escaparHTML(error.message)}</p>`;
    });
    cargarEspacios().catch(error => {
        document.getElementById('spaces-list').innerHTML = `<p class="admin-error">${escaparHTML(error.message)}</p>`;
        document.getElementById('artist-stage').innerHTML = '<option value="">No se pudieron cargar los escenarios</option>';
        document.getElementById('artist-stage').disabled = true;
    });
});
