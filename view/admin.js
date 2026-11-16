// --- DIRECCIÓN DE LA API DE USUARIOS ---
const API_USUARIOS = 'http://127.0.0.1:8001/api';

// --- LÓGICA DE LOGIN ---
document.getElementById('form-login').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    const errorMsg = document.getElementById('login-error');
    
    errorMsg.style.display = 'none';

    try {
        // Hacemos petición al POST de login de main_usuario.py
        const res = await fetch(`${API_USUARIOS}/usuarios/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email, password: password })
        });

        if (res.ok) {
            const datosSesion = await res.json();
            
            // Comprobar si el usuario que ha entrado es administrador
            if (datosSesion.usuario.tipo === 'administrador') {
                // Éxito: Ocultar login y mostrar panel
                document.getElementById('login-container').style.display = 'none';
                document.getElementById('admin-container').style.display = 'flex';
                // (Opcional) Guardar token en sessionStorage si tus otras APIs lo requieren
                sessionStorage.setItem('adminToken', datosSesion.token);
            } else {
                errorMsg.textContent = 'Acceso denegado: No eres administrador.';
                errorMsg.style.display = 'block';
            }
        } else {
            errorMsg.textContent = 'Credenciales incorrectas.';
            errorMsg.style.display = 'block';
        }
    } catch (error) {
        errorMsg.textContent = 'Error: No se pudo conectar con la API de Usuarios (Puerto 8001).';
        errorMsg.style.display = 'block';
    }
});

function cerrarSesion() {
    sessionStorage.removeItem('adminToken');
    document.getElementById('admin-container').style.display = 'none';
    document.getElementById('login-container').style.display = 'block';
    document.getElementById('form-login').reset();
}
// --- LÓGICA DE PESTAÑAS VISUALES ---
// --- LÓGICA DE PESTAÑAS VISUALES ---
function cambiarPestana(idSeccion, botonGatillo) {
    document.querySelectorAll('.admin-section').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
    document.getElementById(idSeccion).classList.add('active');
    botonGatillo.classList.add('active');
}

// --- DIRECCIONES DE TUS MICROSERVICIOS ---
const API_ENTRADAS = 'http://127.0.0.1:8000/api';
const API_ESCALETA = 'http://127.0.0.1:8002/api';
const API_TIENDA = 'http://127.0.0.1:8004/api';

// --- GESTIÓN DE ARTISTAS ---
document.getElementById('form-artista').addEventListener('submit', async (e) => {
    e.preventDefault();
    const datos = {
        nombre: document.getElementById('art-nombre').value,
        genero: document.getElementById('art-genero').value
    };
    try {
        const res = await fetch(`${API_ESCALETA}/escaleta/artistas`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(datos)
        });
        if (res.ok) { alert('¡Artista guardado con éxito!'); e.target.reset(); }
        else { const err = await res.json(); alert(`Revisa el error: ${JSON.stringify(err)}`); }
    } catch (error) { alert('Error: Asegúrate de que la API de Escaleta (8002) está encendida.'); }
});

// --- GESTIÓN DE ENTRADAS ---
document.getElementById('form-entrada').addEventListener('submit', async (e) => {
    e.preventDefault();
    const datos = {
        nombre: document.getElementById('ent-nombre').value,
        precio: parseFloat(document.getElementById('ent-precio').value),
        cantidad: parseInt(document.getElementById('ent-cantidad').value) // o cantidadTotal según tu modelo de Python
    };
    try {
        // NOTA: Ajusta '/entradas' por la ruta exacta de tu main_entradas.py si es diferente
        const res = await fetch(`${API_ENTRADAS}/entradas`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(datos)
        });
        if (res.ok) { alert('¡Entrada guardada con éxito!'); e.target.reset(); }
        else { const err = await res.json(); alert(`Revisa el error: ${JSON.stringify(err)}`); }
    } catch (error) { alert('Error: Asegúrate de que la API de Entradas (8000) está encendida.'); }
});

// --- GESTIÓN DE TIENDA ---
document.getElementById('form-producto').addEventListener('submit', async (e) => {
    e.preventDefault();
    const datos = {
        nombre: document.getElementById('prod-nombre').value,
        categoria: document.getElementById('prod-categoria').value,
        precio: parseFloat(document.getElementById('prod-precio').value),
        stock: parseInt(document.getElementById('prod-stock').value)
    };
    try {
        const res = await fetch(`${API_TIENDA}/merchandising`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(datos)
        });
        if (res.ok) { alert('¡Producto guardado con éxito!'); e.target.reset(); }
        else { const err = await res.json(); alert(`Revisa el error: ${JSON.stringify(err)}`); }
    } catch (error) { alert('Error: Asegúrate de que la API de Tienda (8004) está encendida.'); }
});