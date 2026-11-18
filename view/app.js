function escaparHTML(valor) {
    return String(valor ?? '').replace(/[&<>"']/g, caracter => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[caracter]));
}

const RUTAS = {
    entradas: 'entradas.html',
    escaleta: 'escaleta.html',
    tienda: 'tienda.html',
    admin: 'admin.html'
};

// Puertos configurados según tu backend en Python
const API_ESCALETA = 'http://127.0.0.1:8002/api';
const API_TIENDA = 'http://127.0.0.1:8004/api';

/**
 * Función encargada de redirigir a la sección seleccionada
 */
function navegarA(seccion) {
    const destino = RUTAS[seccion];
    if (destino) {
        window.location.href = destino;
    }
}

/**
 * Muestra un aviso visual en la esquina inferior derecha
 */
function mostrarNotificacion(mensaje) {
    const toast = document.getElementById('toast');
    toast.textContent = mensaje;
    toast.classList.add('show');

    setTimeout(() => {
        toast.classList.remove('show');
    }, 2500);
}

// Inicialización cuando carga el HTML
// Inicialización cuando carga el HTML
document.addEventListener('DOMContentLoaded', () => {
    // Control del menú desplegable en móviles
    const menuBtn = document.getElementById('mobile-menu');
    const navLinks = document.querySelector('.nav-links');

    if (menuBtn && navLinks) {
        menuBtn.addEventListener('click', () => {
            const isExpanded = menuBtn.getAttribute('aria-expanded') === 'true';
            menuBtn.setAttribute('aria-expanded', String(!isExpanded));
            navLinks.classList.toggle('active', !isExpanded);
        });
    }

    if (document.getElementById('api-actuaciones')) {
        cargarInicioDinamico();
    }

    if (document.getElementById('api-programacion')) {
        cargarEscaletaDinamica();
    }
});

/**
 * Conecta con las APIs y renderiza el contenido de inicio
 */
async function cargarInicioDinamico() {
    // Cargar Actuaciones
    try {
        const resAct = await fetch(`${API_ESCALETA}/escaleta`);
        if (resAct.ok) {
            const actuaciones = await resAct.json();
            // Filtramos solo las que no estén canceladas y pillamos las 3 primeras
            const validas = actuaciones.filter(a => a.estado !== 'cancelada').slice(0, 3);
            renderizarActuaciones(validas);
        } else {
            throw new Error("Error en la respuesta");
        }
    } catch (error) {
        document.getElementById('api-actuaciones').innerHTML = 
            '<p style="color:#ff9fbd;">No se pudo conectar con la API de Escaleta (Puerto 8002).</p>';
    }

    // Cargar Productos
    try {
        const resProd = await fetch(`${API_TIENDA}/merchandising/disponibles`);
        if (resProd.ok) {
            const productos = await resProd.json();
            // Pillamos los 4 primeros productos
            renderizarProductos(productos.slice(0, 4));
        } else {
            throw new Error("Error en la respuesta");
        }
    } catch (error) {
        document.getElementById('api-productos').innerHTML = 
            '<p style="color:#ff9fbd;">No se pudo conectar con la API de Tienda (Puerto 8004).</p>';
    }
}

/**
 * Dibuja las tarjetas de actuaciones en el DOM
 */
function renderizarActuaciones(actuaciones) {
    const grid = document.getElementById('api-actuaciones');
    
    if (!actuaciones.length) {
        grid.innerHTML = '<p>No hay actuaciones programadas próximamente.</p>';
        return;
    }

    grid.innerHTML = actuaciones.map(act => `
        <article class="card" onclick="navegarA('escaleta')">
            <div class="card-icon">🎵</div>
            <h3>${escaparHTML(act.nombreArtista)}</h3>
            <p style="margin-bottom: 0.5rem; font-weight: 700;">${escaparHTML(act.nombreEspacio)}</p>
            <p>🗓️ ${escaparHTML(act.fecha.split('-').reverse().join('/'))} &nbsp;|&nbsp; 🕒 ${escaparHTML(act.horaInicio.slice(0, 5))}</p>
            <span class="card-link">Ver en escaleta &rarr;</span>
        </article>
    `).join('');
}

/**
 * Dibuja las tarjetas de productos en el DOM
 */
function renderizarProductos(productos) {
    const grid = document.getElementById('api-productos');
    
    if (!productos.length) {
        grid.innerHTML = '<p>No hay productos en stock en este momento.</p>';
        return;
    }

    grid.innerHTML = productos.map(prod => `
        <article class="shop-card">
            <div class="shop-art">
                <span>${escaparHTML(prod.nombre.substring(0, 3).toUpperCase())}<br>${escaparHTML(prod.categoria.substring(0, 4).toUpperCase())}</span>
            </div>
            <div class="shop-card-content">
                <span class="shop-category">${escaparHTML(prod.categoria.toUpperCase())}</span>
                <h3>${escaparHTML(prod.nombre)}</h3>
                <div class="shop-card-footer">
                    <span class="shop-price">${escaparHTML(prod.precio.toLocaleString('es-ES'))} €</span>
                    <a class="btn shop-buy-button" href="comprar-producto.html?producto=${escaparHTML(prod.id)}">Comprar</a>
                </div>
            </div>
        </article>
    `).join('');

}
// ... (código anterior igual)

/**
 * Dibuja las tarjetas de productos en el DOM
 */
function renderizarProductos(productos) {
    const grid = document.getElementById('api-productos');
    
    if (!productos.length) {
        grid.innerHTML = '<p>No hay productos en stock en este momento.</p>';
        return;
    }

    grid.innerHTML = productos.map(prod => `
        <article class="shop-card">
            <div class="shop-art">
                <span>${escaparHTML(prod.nombre.substring(0, 3).toUpperCase())}<br>${escaparHTML(prod.categoria.substring(0, 4).toUpperCase())}</span>
            </div>
            <div class="shop-card-content">
                <span class="shop-category">${escaparHTML(prod.categoria.toUpperCase())}</span>
                <h3>${escaparHTML(prod.nombre)}</h3>
                <div class="shop-card-footer">
                    <span class="shop-price">${escaparHTML(prod.precio.toLocaleString('es-ES'))} €</span>
                    <a class="btn shop-buy-button" href="comprar-producto.html?producto=${escaparHTML(prod.id)}">Comprar</a>
                </div>
            </div>
        </article>
    `).join('');
} // <-- ¡Esta es la llave que faltaba para cerrar la función!

/**
 * Conecta con la API y obtiene toda la programación
 */
async function cargarEscaletaDinamica() {
    try {
        const respuesta = await fetch(`${API_ESCALETA}/escaleta`);
        
        if (respuesta.ok) {
            const actuaciones = await respuesta.json();
            const validas = actuaciones.filter(a => a.estado !== 'cancelada');
            renderizarEscaleta(validas);
        } else {
            throw new Error("Error en la respuesta");
        }
    } catch (error) {
        document.getElementById('api-programacion').innerHTML = 
            '<p style="color:#ff9fbd; text-align: center;">No se pudo conectar con la API de Escaleta (Puerto 8002).</p>';
    }
}

/**
 * Agrupa los conciertos por escenario y los dibuja
 */
function renderizarEscaleta(actuaciones) {
    const contenedor = document.getElementById('api-programacion');
    
    if (!actuaciones.length) {
        contenedor.innerHTML = '<p style="text-align: center;">Aún no hay actuaciones programadas.</p>';
        return;
    }

    const porEscenario = Object.create(null);
    actuaciones.forEach(act => {
        if (!porEscenario[act.nombreEspacio]) {
            porEscenario[act.nombreEspacio] = [];
        }
        porEscenario[act.nombreEspacio].push(act);
    });

    let html = '';

    for (const escenario in porEscenario) {
        html += `
            <div class="tickets-heading" style="margin-top: 3rem; margin-bottom: 2rem;">
                <div>
                    <span class="eyebrow">ESCENARIO</span>
                    <h2>${escaparHTML(escenario)}</h2>
                </div>
            </div>
            <div class="cards-grid">
        `;

        porEscenario[escenario].forEach(act => {
            const fechaBonita = act.fecha.split('-').reverse().join('/');
            const horaInicio = act.horaInicio.slice(0, 5);
            const horaFin = act.horaFin.slice(0, 5);

            html += `
                <article class="card">
                    <div class="card-icon">🎤</div>
                    <h3>${escaparHTML(act.nombreArtista)}</h3>
                    <p style="margin-bottom: 0.5rem; font-weight: 700;">${escaparHTML(fechaBonita)}</p>
                    <p style="color: var(--text-gray);">🕒 ${escaparHTML(horaInicio)} - ${escaparHTML(horaFin)}</p>
                    <span class="card-link" onclick="mostrarNotificacion('Actuación seleccionada')">Ver detalles &rarr;</span>
                </article>
            `;
        });

        html += `</div>`;
    }

    contenedor.innerHTML = html;
}