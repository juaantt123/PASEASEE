const RUTAS = {
    entradas: 'entradas.html',
    escaleta: 'escaleta.html',
    tienda: 'tienda.html'
};

/**
 * Función encargada de redirigir a la sección seleccionada
 * @param {string} seccion - 'entradas', 'escaleta' o 'tienda'
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

// Control del menú desplegable en móviles
document.addEventListener('DOMContentLoaded', () => {
    const menuBtn = document.getElementById('mobile-menu');
    const navLinks = document.querySelector('.nav-links');

    menuBtn.addEventListener('click', () => {
        const isExpanded = menuBtn.getAttribute('aria-expanded') === 'true';
        menuBtn.setAttribute('aria-expanded', String(!isExpanded));
        navLinks.classList.toggle('active', !isExpanded);
    });
});