const tiposEntrada = {
    dia: { nombre: 'Entrada de día', precio: 25 },
    abono: { nombre: 'Abono general (3 días)', precio: 60 },
    vip: { nombre: 'Abono VIP', precio: 100 }
};

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('checkout-form');
    const typeInput = document.getElementById('ticket-type');
    const quantityInput = document.getElementById('ticket-quantity');
    const summaryTicket = document.getElementById('summary-ticket');
    const summaryQuantity = document.getElementById('summary-quantity');
    const summaryPrice = document.getElementById('summary-price');
    const summaryTotal = document.getElementById('summary-total');
    const message = document.getElementById('checkout-message');
    const cardNumber = document.getElementById('card-number');
    const cardExpiry = document.getElementById('card-expiry');
    const cardCvc = document.getElementById('card-cvc');

    const initialType = new URLSearchParams(window.location.search).get('tipo');
    if (Object.hasOwn(tiposEntrada, initialType)) {
        typeInput.value = initialType;
    }

    const updateSummary = () => {
        const entrada = tiposEntrada[typeInput.value];
        const quantity = Number(quantityInput.value) || 0;
        const formatPrice = (price) => `${price.toLocaleString('es-ES')} €`;

        summaryTicket.textContent = entrada.nombre;
        summaryQuantity.textContent = String(quantity);
        summaryPrice.textContent = formatPrice(entrada.precio);
        summaryTotal.textContent = formatPrice(entrada.precio * quantity);
    };

    typeInput.addEventListener('change', updateSummary);
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
        if (!Number.isInteger(quantity) || quantity < 1 || quantity > 6) {
            quantityInput.setCustomValidity('Selecciona entre 1 y 6 entradas.');
            quantityInput.reportValidity();
            quantityInput.setCustomValidity('');
            return;
        }

        const expiryMatch = cardExpiry.value.match(/^(0[1-9]|1[0-2])\/(\d{2})$/);
        const cardDigits = cardNumber.value;
        if (cardDigits.length < 13 || cardDigits.length > 19) {
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

        message.textContent = 'Datos validados para la demostración. No se ha realizado ningún pago ni se ha guardado la información.';
        message.classList.add('is-success');
        cardNumber.value = '';
        cardExpiry.value = '';
        cardCvc.value = '';
        document.getElementById('cardholder-name').value = '';
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
