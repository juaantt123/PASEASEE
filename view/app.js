// Configuración de las rutas de vuestro proyecto
// Cuando tengáis listos los archivos HTML de cada sección, poned aquí sus nombres reales:
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
        mostrarNotificacion(`Abriendo sección de ${seccion.toUpperCase()}...`);
        
        // Pequeño retardo visual de 600ms antes de cambiar de página
        // Si ya tenéis los archivos creados, descomenta la línea de window.location.href
        setTimeout(() => {
            console.log(`Redirigiendo a: ${destino}`);
            // window.location.href = destino; 
        }, 600);
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
        navLinks.classList.toggle('active');
    });
});