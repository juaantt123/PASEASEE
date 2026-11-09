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

document.addEventListener('DOMContentLoaded', () => {
    const productId = new URLSearchParams(window.location.search).get('producto');
    const product = productosTienda[productId];
    const form = document.getElementById('product-checkout-form');
    const message = document.getElementById('product-checkout-message');
    const cardNumber = document.getElementById('card-number');
    const cardExpiry = document.getElementById('card-expiry');
    const cardCvc = document.getElementById('card-cvc');

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

    cardNumber.addEventListener('input', () => {
        cardNumber.value = cardNumber.value.replace(/\D/g, '').slice(0, 19);
    });

    cardExpiry.addEventListener('input', () => {
        const digits = cardExpiry.value.replace(/\D/g, '').slice(0, 4);
        cardExpiry.value = digits.length > 2 ? `${digits.slice(0, 2)}/${digits.slice(2)}` : digits;
    });

    cardCvc.addEventListener('input', () => {
        cardCvc.value = cardCvc.value.replace(/\D/g, '').slice(0, 4);
    });

    form.addEventListener('submit', (event) => {
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

        const expiryMatch = cardExpiry.value.match(/^(0[1-9]|1[0-2])\/(\d{2})$/);
        if (cardNumber.value.length < 13 || cardNumber.value.length > 19) {
            cardNumber.setCustomValidity('Introduce un número de tarjeta de prueba de 13 a 19 dígitos.');
            cardNumber.reportValidity();
            cardNumber.setCustomValidity('');
            return;
        }

        if (!expiryMatch || !isExpiryCurrent(expiryMatch)) {
            cardExpiry.setCustomValidity('Introduce una fecha válida que no haya caducado (MM/AA).');
            cardExpiry.reportValidity();
            cardExpiry.setCustomValidity('');
            return;
        }

        if (!/^\d{3,4}$/.test(cardCvc.value)) {
            cardCvc.setCustomValidity('El CVV de prueba debe tener 3 o 4 dígitos.');
            cardCvc.reportValidity();
            cardCvc.setCustomValidity('');
            return;
        }

        message.textContent = 'Pedido preparado para la demostración. No se ha realizado ningún cobro ni se han guardado tus datos.';
        message.classList.add('is-success');
        form.reset();
        productName.value = product.nombre;
        updateSummary();
    });
});

function isExpiryCurrent(match) {
    const month = Number(match[1]);
    const shortYear = Number(match[2]);
    const currentDate = new Date();
    let year = Math.floor(currentDate.getFullYear() / 100) * 100 + shortYear;

    if (year < currentDate.getFullYear() - 80) {
        year += 100;
    }

    return year > currentDate.getFullYear()
        || (year === currentDate.getFullYear() && month >= currentDate.getMonth() + 1);
}
