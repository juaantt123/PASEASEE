const API_USUARIOS_COMPRA = [
    window.SUBSONIC_API_URL,
    'http://127.0.0.1:8001/api/usuarios',
    'http://localhost:8001/api/usuarios',
    'http://127.0.0.1:8000/api/usuarios'
].filter(Boolean);

const API_ENTRADAS_COMPRA = [
    window.SUBSONIC_ENTRADAS_API_URL,
    'http://127.0.0.1:8000/api/entradas',
    'http://localhost:8000/api/entradas',
    'http://127.0.0.1:8081/api/entradas'
].filter(Boolean);

const CLAVE_SESION_COMPRA = 'subsonic-sesion';

document.addEventListener('DOMContentLoaded', iniciarCompraEntradas);

async function iniciarCompraEntradas() {
    const form = document.getElementById('checkout-form');
    if (!form) return;

    const tipoSelect = document.getElementById('ticket-type');
    const cantidadInput = document.getElementById('ticket-quantity');
    const mensaje = document.getElementById('checkout-message');
    const boton = document.getElementById('checkout-submit');
    const loginLink = document.getElementById('checkout-login-link');
    const usuarioStatus = document.getElementById('checkout-user-status');
    const sesion = leerSesionCompra();
    let tipos = [];

    if (sesion?.usuario?.id && sesion?.token) {
        usuarioStatus.textContent = `Sesión iniciada como ${sesion.usuario.nombre} ${sesion.usuario.apellidos}.`;
        loginLink.hidden = true;
    } else {
        usuarioStatus.textContent = 'Inicia sesión antes de comprar una entrada.';
    }

    const params = new URLSearchParams(window.location.search);
    const idSeleccionado = params.get('idTipoEntrada');
    const tipoAntiguo = {
        dia: 'abono_un_dia',
        abono: 'abono_completo',
        vip: 'vip'
    }[params.get('tipo')];

    try {
        tipos = await solicitarCompra(API_ENTRADAS_COMPRA, '/disponibles');
        tipoSelect.replaceChildren();
        tipos.forEach((tipo) => {
            const opcion = document.createElement('option');
            opcion.value = String(tipo.id);
            opcion.textContent = `${nombreEntrada(tipo.nombre)} — ${formatearPrecio(tipo.precio)} (${tipo.stockDisponible} disponibles)`;
            tipoSelect.appendChild(opcion);
        });
        tipoSelect.disabled = tipos.length === 0;

        const porId = tipos.find((tipo) => String(tipo.id) === idSeleccionado);
        const porNombre = tipos.find((tipo) => tipo.nombre === tipoAntiguo);
        if (porId || porNombre) tipoSelect.value = String((porId || porNombre).id);
        actualizarResumen(tipoSelect, cantidadInput, tipos);
    } catch (error) {
        tipoSelect.replaceChildren(new Option('No se pudo cargar el catálogo', ''));
        tipoSelect.disabled = true;
        mensaje.textContent = error.message;
    }

    tipoSelect.addEventListener('change', () => actualizarResumen(tipoSelect, cantidadInput, tipos));
    cantidadInput.addEventListener('input', () => actualizarResumen(tipoSelect, cantidadInput, tipos));

    const cardNumber = document.getElementById('card-number');
    const cardExpiry = document.getElementById('card-expiry');
    const cardCvc = document.getElementById('card-cvc');
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

    boton.disabled = !sesion?.usuario?.id || !sesion?.token || tipos.length === 0;

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        mensaje.textContent = '';
        mensaje.classList.remove('is-success');

        if (!sesion?.usuario?.id || !sesion?.token) {
            mensaje.textContent = 'Inicia sesión desde Perfil para asociar la compra a tu cuenta.';
            return;
        }
        if (!form.reportValidity()) return;

        const cantidad = Number(cantidadInput.value);
        if (!Number.isInteger(cantidad) || cantidad < 1 || cantidad > 6) {
            cantidadInput.setCustomValidity('Selecciona entre 1 y 6 entradas.');
            cantidadInput.reportValidity();
            cantidadInput.setCustomValidity('');
            return;
        }

        const tipoActual = tipos.find((tipo) => String(tipo.id) === tipoSelect.value);
        if (!tipoActual) {
            mensaje.textContent = 'Selecciona un tipo de entrada disponible.';
            return;
        }

        const caducidad = cardExpiry.value.match(/^(0[1-9]|1[0-2])\/(\d{2})$/);
        if (!caducidad || !esCaducidadValida(caducidad)) {
            cardExpiry.setCustomValidity('Introduce una fecha válida y vigente (MM/AA).');
            cardExpiry.reportValidity();
            cardExpiry.setCustomValidity('');
            return;
        }
        if (!/^\d{3,4}$/.test(cardCvc.value)) {
            cardCvc.setCustomValidity('El CVV ficticio debe tener 3 o 4 dígitos.');
            cardCvc.reportValidity();
            cardCvc.setCustomValidity('');
            return;
        }

        boton.disabled = true;
        boton.textContent = 'Registrando compra…';
        try {
            // Usuarios conserva solo los últimos cuatro dígitos; nunca enviamos el CVV.
            const metodo = await solicitarCompra(
                API_USUARIOS_COMPRA,
                `/${sesion.usuario.id}/metodos-pago`,
                {
                    method: 'POST',
                    body: JSON.stringify({
                        tipo: 'tarjeta',
                        titular: document.getElementById('cardholder-name').value.trim(),
                        numero: cardNumber.value,
                        fechaCaducidad: cardExpiry.value,
                        predeterminado: false
                    })
                }
            );

            const compra = await solicitarCompra(
                API_ENTRADAS_COMPRA,
                '/comprar',
                {
                    method: 'POST',
                    body: JSON.stringify({
                        idUsuario: sesion.usuario.id,
                        idTipoEntrada: tipoActual.id,
                        cantidad,
                        idMetodoPago: metodo.id
                    })
                }
            );

            mensaje.textContent = `Compra registrada. Referencia ${compra.idCompra}; ${compra.cantidad} entrada(s), total ${formatearPrecio(compra.precioTotal)}. Consulta tus entradas en Perfil.`;
            mensaje.classList.add('is-success');
            cardNumber.value = '';
            cardExpiry.value = '';
            cardCvc.value = '';
            document.getElementById('cardholder-name').value = '';

            const actualizadas = await solicitarCompra(API_ENTRADAS_COMPRA, '/disponibles');
            tipos = actualizadas;
            const seleccionPrevia = String(tipoActual.id);
            tipoSelect.replaceChildren();
            tipos.forEach((tipo) => {
                const opcion = new Option(
                    `${nombreEntrada(tipo.nombre)} — ${formatearPrecio(tipo.precio)} (${tipo.stockDisponible} disponibles)`,
                    String(tipo.id)
                );
                tipoSelect.appendChild(opcion);
            });
            tipoSelect.value = tipos.some((tipo) => String(tipo.id) === seleccionPrevia)
                ? seleccionPrevia
                : (tipos[0] ? String(tipos[0].id) : '');
            tipoSelect.disabled = tipos.length === 0;
            actualizarResumen(tipoSelect, cantidadInput, tipos);
        } catch (error) {
            mensaje.textContent = error.message;
        } finally {
            boton.textContent = 'Comprar entrada (demo)';
            boton.disabled = !sesion?.usuario?.id || !sesion?.token || tipos.length === 0;
        }
    });
}

function actualizarResumen(tipoSelect, cantidadInput, tipos) {
    const tipo = tipos.find((item) => String(item.id) === tipoSelect.value);
    const cantidad = Number(cantidadInput.value) || 0;
    document.getElementById('summary-ticket').textContent = tipo ? nombreEntrada(tipo.nombre) : '—';
    document.getElementById('summary-quantity').textContent = String(cantidad);
    document.getElementById('summary-price').textContent = tipo ? formatearPrecio(tipo.precio) : '—';
    document.getElementById('summary-total').textContent = tipo
        ? formatearPrecio(tipo.precio * cantidad)
        : '—';
}

function leerSesionCompra() {
    try {
        return JSON.parse(sessionStorage.getItem(CLAVE_SESION_COMPRA) || 'null');
    } catch {
        return null;
    }
}

async function solicitarCompra(bases, ruta, opciones = {}) {
    let ultimoError;
    for (const base of bases) {
        let respuesta;
        try {
            respuesta = await fetch(`${base}${ruta}`, {
                ...opciones,
                headers: { 'Content-Type': 'application/json', ...opciones.headers }
            });
        } catch {
            continue;
        }

        let cuerpo;
        try {
            cuerpo = await respuesta.json();
        } catch {
            ultimoError = new Error('El servicio devolvió una respuesta no válida.');
            continue;
        }
        if (respuesta.status === 404 || respuesta.status === 405) continue;
        if (!respuesta.ok) {
            throw new Error(cuerpo.mensaje || cuerpo.detail || 'No se pudo completar la operación.');
        }
        return cuerpo;
    }
    throw ultimoError || new Error('No se pudo conectar con el servicio. Comprueba que esté iniciado.');
}

function nombreEntrada(nombre) {
    return {
        abono_un_dia: 'Entrada de día',
        abono_completo: 'Abono general',
        vip: 'Abono VIP'
    }[nombre] || nombre;
}

function formatearPrecio(precio) {
    return `${Number(precio).toLocaleString('es-ES')} €`;
}

function esCaducidadValida(match) {
    const mes = Number(match[1]);
    const anioCorto = Number(match[2]);
    const ahora = new Date();
    let anio = Math.floor(ahora.getFullYear() / 100) * 100 + anioCorto;
    if (anio < ahora.getFullYear() - 80) anio += 100;
    return anio > ahora.getFullYear()
        || (anio === ahora.getFullYear() && mes >= ahora.getMonth() + 1);
}
