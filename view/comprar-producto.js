const API_USUARIOS_TIENDA = 'http://127.0.0.1:8001/api/usuarios';

async function solicitarTienda(url, opciones = {}) {
    let respuesta;
    try {
        respuesta = await fetch(url, opciones);
    } catch {
        throw new Error('No se pudo conectar con el servicio. Comprueba que esté iniciado.');
    }
    let datos;
    try { datos = await respuesta.json(); }
    catch { throw new Error('El servicio devolvió una respuesta no válida.'); }
    if (!respuesta.ok) throw new Error(datos.mensaje || datos.detail || `Error ${respuesta.status}`);
    return datos;
}

document.addEventListener('DOMContentLoaded', async () => {
    const form = document.getElementById('product-checkout-form');
    const mensaje = document.getElementById('product-checkout-message');
    const boton = document.getElementById('product-submit');
    const cantidad = document.getElementById('product-quantity');
    const talla = document.getElementById('product-size');
    const metodos = document.getElementById('payment-method');
    const id = Number(new URLSearchParams(location.search).get('producto'));
    let sesion;
    try { sesion = JSON.parse(sessionStorage.getItem('subsonic-sesion') || 'null'); }
    catch { sesion = null; }
    if (!Number.isInteger(id) || id < 1) {
        mensaje.textContent = 'Selecciona un producto desde la tienda.';
        return;
    }
    if (!sesion?.usuario?.id || !sesion?.token) {
        mensaje.textContent = 'Inicia sesión desde Perfil para realizar el pedido.';
        return;
    }
    let producto;
    let metodosDisponibles;
    try {
        const usuario = await solicitarTienda(`${API_USUARIOS_TIENDA}/sesion`, {
            headers: { Authorization: `Bearer ${sesion.token}` }
        });
        if (usuario.id !== sesion.usuario.id) throw new Error('La sesión no corresponde a la cuenta seleccionada.');
        [producto, metodosDisponibles] = await Promise.all([
            solicitarTienda(`${API_TIENDA}/merchandising/${id}`),
            solicitarTienda(`${API_USUARIOS_TIENDA}/${usuario.id}/metodos-pago`)
        ]);
    } catch (error) {
        mensaje.textContent = error.message;
        return;
    }
    document.getElementById('product-name').value = producto.nombre;
    document.getElementById('summary-product').textContent = producto.nombre;
    const precio = n => `${Number(n).toLocaleString('es-ES', { minimumFractionDigits: 2 })} €`;
    document.getElementById('summary-unit-price').textContent = precio(producto.precio);
    const necesitaTalla = ['camiseta', 'sudadera'].includes(producto.categoria);
    document.getElementById('talla-grupo').hidden = !necesitaTalla;
    talla.required = necesitaTalla;
    metodos.replaceChildren(new Option('Selecciona un método', ''));
    for (const metodo of metodosDisponibles) {
        const etiqueta = metodo.tipo === 'tarjeta' ? `Tarjeta terminada en ${metodo.ultimosDigitos || '????'}` : 'PayPal';
        metodos.add(new Option(etiqueta, String(metodo.id)));
    }
    if (!metodosDisponibles.length) mensaje.textContent = 'No tienes métodos de pago de prueba. Añade uno mediante la API de Usuarios.';
    if (!producto.disponible || producto.stock <= 0) mensaje.textContent = 'Este producto está agotado.';
    boton.disabled = !metodosDisponibles.length || !producto.disponible || producto.stock <= 0;
    const actualizarResumen = () => {
        document.getElementById('summary-product-quantity').textContent = cantidad.value;
        document.getElementById('summary-product-total').textContent = precio(Number(cantidad.value) * producto.precio);
    };
    cantidad.addEventListener('input', actualizarResumen);
    actualizarResumen();
    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (!form.reportValidity()) return;
        mensaje.textContent = '';
        mensaje.classList.remove('is-success');
        boton.disabled = true;
        try {
            const compra = await solicitarTienda(`${API_TIENDA}/merchandising/compras`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ idUsuario: sesion.usuario.id, idProducto: id, cantidad: Number(cantidad.value), talla: necesitaTalla ? talla.value : null, idMetodoPago: Number(metodos.value) })
            });
            mensaje.textContent = `Pedido registrado. Referencia ${compra.idCompra}; total ${precio(compra.precioTotal)}. No se ha realizado ningún cobro.`;
            mensaje.classList.add('is-success');
            // Evita duplicar la compra si se vuelve a pulsar el botón.
            boton.textContent = 'Pedido registrado';
        } catch (error) {
            mensaje.textContent = error.message;
            boton.disabled = false;
        }
    });
});
