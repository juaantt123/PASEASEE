const productosTienda = {
    camiseta: { nombre: 'Camiseta oficial', precio: 25 },
    sudadera: { nombre: 'Sudadera del festival', precio: 55 },
    poster: { nombre: 'Póster edición 2026', precio: 12 },
    kit: { nombre: 'Kit de festival', precio: 18 },
    bolsa: { nombre: 'Bolsa tote', precio: 15 },
    gorra: { nombre: 'Gorra Subsonic', precio: 20 },
    botella: { nombre: 'Botella reutilizable', precio: 18 },
    gafas: { nombre: 'Gafas festivaleras', precio: 10 },
    pulsera: { nombre: 'Pulsera conmemorativa', precio: 5 },
    rinonera: { nombre: 'Riñonera festival', precio: 28 },
    tapones: { nombre: 'Tapones para conciertos', precio: 8 },
    abanico: { nombre: 'Abanico Subsonic', precio: 12 }
};

const API_BASES_USUARIOS_TIENDA = [
    window.SUBSONIC_API_URL,
    'http://localhost:8000/api/usuarios',
    'http://127.0.0.1:8081/api/usuarios',
    'http://127.0.0.1:8001/api/usuarios'
].filter(Boolean);

document.addEventListener('DOMContentLoaded', () => {
    const productId = new URLSearchParams(window.location.search).get('producto');
    const product = productosTienda[productId];
    const form = document.getElementById('product-checkout-form');
    const message = document.getElementById('product-checkout-message');

    if (!product) {
        window.location.replace('tienda.html');
        return;
    }

    const productName = document.getElementById('product-name');
    const quantityInput = document.getElementById('product-quantity');
    const summaryProduct = document.getElementById('summary-product');
    const summaryUnitPrice = document.getElementById('summary-unit-price');
    const summaryQuantity = document.getElementById('summary-product-quantity');
    const summaryTotal = document.getElementById('summary-product-total');
    const formatPrice = (price) => `${price.toLocaleString('es-ES')} €`;

    productName.value = product.nombre;
    summaryProduct.textContent = product.nombre;
    summaryUnitPrice.textContent = formatPrice(product.precio);

    const updateSummary = () => {
        const quantity = Number(quantityInput.value) || 0;
        summaryQuantity.textContent = String(quantity);
        summaryTotal.textContent = formatPrice(quantity * product.precio);
    };

    quantityInput.addEventListener('input', updateSummary);
    updateSummary();

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        message.textContent = '';
        message.classList.remove('is-success');

        if (!form.reportValidity()) {
            return;
        }

        const quantity = Number(quantityInput.value);
        if (!Number.isInteger(quantity) || quantity < 1 || quantity > 10) {
            quantityInput.setCustomValidity('Selecciona entre 1 y 10 unidades.');
            quantityInput.reportValidity();
            quantityInput.setCustomValidity('');
            return;
        }

        const session = readShopSession();
        if (!session?.usuario?.id || !session?.token) {
            message.textContent = 'Inicia sesión en tu perfil y añade saldo demostrativo antes de realizar el pedido.';
            return;
        }

        try {
            const importe = product.precio * quantity;
            const result = await spendDemoBalance(session, importe, product.nombre);
            message.textContent = `Pedido demo preparado. Se descontaron ${formatPrice(importe)}; saldo disponible: ${formatPrice(result.saldo)}.`;
            message.classList.add('is-success');
            form.reset();
            productName.value = product.nombre;
            updateSummary();
        } catch (error) {
            message.textContent = error.message;
        }
    });
});

function readShopSession() {
    try {
        const storedSession = sessionStorage.getItem('subsonic-sesion');
        return storedSession ? JSON.parse(storedSession) : null;
    } catch {
        return null;
    }
}

function formatPrice(price) {
    return `${price.toLocaleString('es-ES')} €`;
}

async function spendDemoBalance(session, amount, productName) {
    let lastError;
    for (const baseUrl of API_BASES_USUARIOS_TIENDA) {
        let response;
        try {
            response = await fetch(`${baseUrl}/${session.usuario.id}/saldo/gastar`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: 'Bearer ' + session.token
                },
                body: JSON.stringify({
                    importe: amount,
                    concepto: `Compra demo: ${productName}`
                })
            });
        } catch {
            continue;
        }

        let result;
        try {
            result = await response.json();
        } catch {
            lastError = new Error('El servicio de saldo devolvió una respuesta no válida.');
            continue;
        }

        if (response.status === 404 || response.status === 405) {
            continue;
        }
        if (!response.ok) {
            throw new Error(result.mensaje || 'No se pudo completar el pedido.');
        }
        return result;
    }

    throw lastError || new Error('No se pudo conectar con el monedero demo. Comprueba que el servicio de usuarios esté iniciado.');
}
