const API_USUARIOS_PROVEEDOR = 'http://127.0.0.1:8001/api/usuarios';
const SESION_PROVEEDOR = 'subsonic-sesion';
const API_PRODUCTOS_PROVEEDOR = 'http://127.0.0.1:8004/api/merchandising/proveedor/productos';
let tokenProveedor = '';
let productosProveedor = [];

async function pedirProductos(ruta = '', opciones = {}) {
    const respuesta = await fetch(API_PRODUCTOS_PROVEEDOR + ruta, {
        ...opciones, headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${tokenProveedor}` }
    });
    if (!respuesta.ok) {
        let error; try { error = await respuesta.json(); } catch { error = {}; }
        throw new Error(error.mensaje || `Error ${respuesta.status}`);
    }
    return respuesta.status === 204 ? null : respuesta.json();
}

async function cargarProductosProveedor() {
    const estado = document.getElementById('products-status');
    const contenedor = document.getElementById('provider-products');
    contenedor.replaceChildren();
    try {
        productosProveedor = await pedirProductos();
        estado.textContent = productosProveedor.length ? '' : 'Todavía no tienes productos.';
        for (const producto of productosProveedor) {
            const tarjeta = document.createElement('article'); tarjeta.className = 'card';
            const titulo = document.createElement('h3'); titulo.textContent = producto.nombre;
            const detalle = document.createElement('p'); detalle.textContent = `${producto.categoria} · ${producto.precio} € · ${producto.stock} unidades`;
            const editar = document.createElement('button'); editar.className = 'btn'; editar.type = 'button'; editar.textContent = 'Editar';
            editar.addEventListener('click', () => editarProductoProveedor(producto));
            const borrar = document.createElement('button'); borrar.className = 'btn'; borrar.type = 'button'; borrar.textContent = 'Eliminar';
            borrar.addEventListener('click', async () => {
                if (!confirm(`¿Eliminar ${producto.nombre}?`)) return;
                try { await pedirProductos(`/${producto.id}`, { method: 'DELETE' }); await cargarProductosProveedor(); }
                catch (error) { estado.textContent = error.message; }
            });
            tarjeta.append(titulo, detalle, editar, borrar); contenedor.append(tarjeta);
        }
    } catch (error) { estado.textContent = `No se pudieron cargar tus productos: ${error.message}`; }
}

function editarProductoProveedor(producto) {
    document.getElementById('product-id').value = producto.id;
    document.getElementById('product-name').value = producto.nombre;
    document.getElementById('product-description').value = producto.descripcion || '';
    document.getElementById('product-category').value = producto.categoria;
    document.getElementById('product-price').value = producto.precio;
    document.getElementById('product-stock').value = producto.stock;
    document.getElementById('provider-form').scrollIntoView();
}

document.getElementById('product-cancel').addEventListener('click', () => {
    document.getElementById('provider-form').reset(); document.getElementById('product-id').value = '';
});

document.getElementById('provider-form').addEventListener('submit', async evento => {
    evento.preventDefault();
    const id = document.getElementById('product-id').value;
    const anterior = productosProveedor.find(p => String(p.id) === id);
    const datos = {
        nombre: document.getElementById('product-name').value.trim(),
        descripcion: document.getElementById('product-description').value.trim() || null,
        categoria: document.getElementById('product-category').value,
        precio: Number(document.getElementById('product-price').value),
        stock: Number(document.getElementById('product-stock').value),
        imagen: anterior?.imagen || null
    };
    if (!datos.nombre) { document.getElementById('products-status').textContent = 'Introduce un nombre.'; return; }
    try {
        await pedirProductos(id ? `/${id}` : '', { method: id ? 'PUT' : 'POST', body: JSON.stringify(datos) });
        evento.target.reset(); document.getElementById('product-id').value = '';
        await cargarProductosProveedor();
    } catch (error) { document.getElementById('products-status').textContent = error.message; }
});

async function iniciarProveedor() {
    const status = document.getElementById('provider-status');
    let sesion;
    try { sesion = JSON.parse(sessionStorage.getItem(SESION_PROVEEDOR)); } catch { sesion = null; }
    if (!sesion?.token) {
        status.textContent = 'Inicia sesión desde Perfil con tu cuenta de proveedor.';
        return;
    }
    try {
        const respuesta = await fetch(`${API_USUARIOS_PROVEEDOR}/sesion`, {
            headers: { Authorization: `Bearer ${sesion.token}` }
        });
        if (respuesta.status === 401 || respuesta.status === 403) {
            status.textContent = 'Tu sesión no es válida. Vuelve a iniciar sesión en Perfil.';
            return;
        }
        if (!respuesta.ok) throw new Error('Error de Usuarios');
        const usuario = await respuesta.json();
        if (usuario.tipo !== 'proveedor') {
            status.textContent = 'Esta página está disponible para cuentas de proveedor.';
            return;
        }
        tokenProveedor = sesion.token;
        document.getElementById('provider-name').textContent = usuario.nombre;
        document.getElementById('provider-email').textContent = usuario.email;
        document.getElementById('provider-content').hidden = false;
        status.textContent = 'Tu cuenta de proveedor está activa.';
        await cargarProductosProveedor();
    } catch {
        status.textContent = 'No se pudo conectar con la API de Usuarios. Comprueba que está iniciada.';
    }
}

document.getElementById('provider-logout').addEventListener('click', () => {
    sessionStorage.removeItem(SESION_PROVEEDOR);
    sessionStorage.removeItem('tipoUsuario');
    window.location.href = 'perfil.html';
});
iniciarProveedor();
