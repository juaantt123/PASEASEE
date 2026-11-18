const API_BASES_USUARIOS = [
    window.SUBSONIC_API_URL,
    'http://localhost:8000/api/usuarios',
    'http://127.0.0.1:8081/api/usuarios',
    'http://127.0.0.1:8001/api/usuarios'
].filter(Boolean);
const API_BASES_ENTRADAS = [
    window.SUBSONIC_ENTRADAS_API_URL,
    'http://127.0.0.1:8000/api/entradas',
    'http://127.0.0.1:8081/api/entradas'
].filter(Boolean);
const CLAVE_SESION = 'subsonic-sesion';
document.addEventListener('DOMContentLoaded', () => {
    const authContainer = document.getElementById('account-auth');
    const profilePanel = document.getElementById('profile-panel');
    const message = document.getElementById('account-message');
    const loginTab = document.getElementById('login-tab');
    const registerTab = document.getElementById('register-tab');
    const loginPanel = document.getElementById('login-panel');
    const registerPanel = document.getElementById('register-panel');
    let session = readSession();

    const showMessage = (text, isSuccess = false) => {
        message.textContent = text;
        message.classList.toggle('is-success', isSuccess);
    };

    const setTab = (tab) => {
        const isLogin = tab === 'login';
        loginTab.classList.toggle('active', isLogin);
        registerTab.classList.toggle('active', !isLogin);
        loginTab.setAttribute('aria-selected', String(isLogin));
        registerTab.setAttribute('aria-selected', String(!isLogin));
        loginPanel.hidden = !isLogin;
        registerPanel.hidden = isLogin;
        showMessage('');
    };

    const renderProfile = (user) => {
        authContainer.hidden = true;
        profilePanel.hidden = false;
        document.getElementById('profile-display-name').textContent =
            `${user.nombre} ${user.apellidos}`.trim();
        document.getElementById('profile-display-email').textContent = user.email;
        document.getElementById('profile-name').value = user.nombre || '';
        document.getElementById('profile-surname').value = user.apellidos || '';
        document.getElementById('profile-phone').value = user.telefono || '';
        document.getElementById('profile-birthdate').value = user.fechaNacimiento || '';
        loadAccountDashboard(user.id, session.token);
    };

    const saveSession = (newSession) => {
        session = newSession;
        let persisted = true;
        try {
            sessionStorage.setItem(CLAVE_SESION, JSON.stringify(newSession));
        } catch {
            persisted = false;
        }
        renderProfile(newSession.usuario);
        return persisted;
    };

    loginTab.addEventListener('click', () => setTab('login'));
    registerTab.addEventListener('click', () => setTab('register'));

    document.getElementById('register-birthdate').max = new Date().toISOString().slice(0, 10);
    document.getElementById('profile-birthdate').max = new Date().toISOString().slice(0, 10);

    document.getElementById('register-form').addEventListener('submit', async (event) => {
        event.preventDefault();
        showMessage('');

        const form = event.currentTarget;
        if (!form.reportValidity()) {
            return;
        }

        const password = document.getElementById('register-password').value;
        const confirmPassword = document.getElementById('register-confirm-password');
        if (password !== confirmPassword.value) {
            confirmPassword.setCustomValidity('Las contraseñas no coinciden.');
            confirmPassword.reportValidity();
            confirmPassword.setCustomValidity('');
            return;
        }

        const birthDate = document.getElementById('register-birthdate').value;
        const payload = {
            nombre: document.getElementById('register-name').value.trim(),
            apellidos: document.getElementById('register-surname').value.trim(),
            email: document.getElementById('register-email').value.trim(),
            password,
            telefono: document.getElementById('register-phone').value.trim() || null,
            fechaNacimiento: birthDate || null,
            tipo: 'cliente'
        };

        try {
            await requestApi('/api/usuarios', {
                method: 'POST',
                body: JSON.stringify(payload)
            });
            document.getElementById('login-email').value = payload.email;
            document.getElementById('login-password').value = '';
            form.reset();
            setTab('login');
            showMessage('Cuenta creada. Inicia sesión con tu correo y contraseña.', true);
        } catch (error) {
            showMessage(error.message);
        }
    });

    document.getElementById('login-form').addEventListener('submit', async (event) => {
        event.preventDefault();
        showMessage('');

        const form = event.currentTarget;
        if (!form.reportValidity()) {
            return;
        }

        try {
            const result = await requestApi('/api/usuarios/login', {
                method: 'POST',
                body: JSON.stringify({
                    email: document.getElementById('login-email').value.trim(),
                    password: document.getElementById('login-password').value
                })
            });

            document.getElementById('login-password').value = '';
            
            // LA MAGIA: Si el usuario es administrador, lo mandamos al panel oculto
            if (result.usuario.tipo === 'administrador') {
                sessionStorage.setItem(CLAVE_SESION, JSON.stringify(result));
                sessionStorage.setItem('tipoUsuario', 'administrador');
                window.location.href = 'admin.html';
                return; // Cortamos aquí para que no siga cargando el perfil
            }

            // Si es un cliente normal, sigue el flujo habitual
            sessionStorage.setItem('tipoUsuario', 'cliente');
            const persisted = saveSession(result);
            showMessage(
                persisted
                    ? `¡Bienvenido/a, ${result.usuario.nombre}!`
                    : `¡Bienvenido/a, ${result.usuario.nombre}! La sesión solo durará mientras esta página siga abierta.`,
                true
            );
        } catch (error) {
            showMessage(error.message);
        }
    });

    document.getElementById('profile-form').addEventListener('submit', async (event) => {
        event.preventDefault();
        showMessage('');

        const form = event.currentTarget;
        if (!form.reportValidity()) {
            return;
        }

        const payload = {
            nombre: document.getElementById('profile-name').value.trim(),
            apellidos: document.getElementById('profile-surname').value.trim(),
            telefono: document.getElementById('profile-phone').value.trim() || null,
            fechaNacimiento: document.getElementById('profile-birthdate').value || null
        };

        try {
            const updatedUser = await requestApi(
                `/api/usuarios/${session.usuario.id}/perfil`,
                {
                    method: 'PATCH',
                    headers: { Authorization: 'Bearer ' + session.token },
                    body: JSON.stringify(payload)
                }
            );
            const persisted = saveSession({ ...session, usuario: updatedUser });
            showMessage(
                persisted
                    ? 'Los datos de tu perfil se han actualizado.'
                    : 'Perfil actualizado. La sesión solo durará mientras esta página siga abierta.',
                true
            );
        } catch (error) {
            showMessage(error.message);
        }
    });

    document.getElementById('logout-button').addEventListener('click', () => {
        session = null;
        try {
            sessionStorage.removeItem(CLAVE_SESION);
        } catch {
            session = null;
        }
        profilePanel.hidden = true;
        authContainer.hidden = false;
        document.getElementById('login-form').reset();
        setTab('login');
        showMessage('Has cerrado sesión.', true);
    });

    if (session?.usuario?.id && session?.token) {
        renderProfile(session.usuario);
    }

    document.getElementById('wallet-form').addEventListener('submit', async (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const status = document.getElementById('wallet-status');
        status.textContent = '';

        if (!form.reportValidity()) {
            return;
        }

        try {
            const result = await requestApi(`/api/usuarios/${session.usuario.id}/saldo/recargar`, {
                method: 'POST',
                headers: { Authorization: 'Bearer ' + session.token },
                body: JSON.stringify({
                    importe: Number(document.getElementById('wallet-amount').value),
                    concepto: 'Recarga de saldo demo'
                })
            });
            renderWalletBalance(result.saldo);
            status.textContent = 'Crédito demostrativo añadido. No se ha realizado ningún cobro.';
            status.classList.add('is-success');
        } catch (error) {
            status.textContent = error.message;
            status.classList.remove('is-success');
        }
    });
});

async function renderSchedule() {
    const container = document.getElementById('account-schedule');
    container.replaceChildren();
    try {
        const response = await fetch('http://127.0.0.1:8002/api/escaleta');
        if (!response.ok) throw new Error('No se pudo consultar Escaleta.');
        const actuaciones = (await response.json()).filter(a => a.estado !== 'cancelada');
        actuaciones.sort((a, b) => (a.fecha + a.horaInicio).localeCompare(b.fecha + b.horaInicio));
        if (!actuaciones.length) { container.textContent = 'No hay actuaciones programadas.'; return; }
        const dias = new Map();
        for (const a of actuaciones) {
            if (!dias.has(a.fecha)) dias.set(a.fecha, []);
            dias.get(a.fecha).push(a);
        }
        for (const [fecha, artistas] of dias) {
            const card = document.createElement('article'); card.className = 'account-day-card';
            const heading = document.createElement('h5'); heading.textContent = formatDate(fecha);
            const list = document.createElement('ul');
            for (const a of artistas) {
                const item = document.createElement('li');
                const hora = document.createElement('strong'); hora.textContent = `${a.horaInicio.slice(0, 5)}–${a.horaFin.slice(0, 5)}`;
                const artista = document.createElement('span'); artista.textContent = a.nombreArtista;
                const espacio = document.createElement('small'); espacio.textContent = a.nombreEspacio;
                item.append(hora, artista, espacio); list.append(item);
            }
            card.append(heading, list); container.append(card);
        }
    } catch { container.textContent = 'No se pudo cargar la programación de Escaleta.'; }
}

async function loadAccountDashboard(userId, token) {
    renderSchedule();
    await Promise.all([
        loadPurchasedTickets(userId, token),
        loadWalletBalance(userId, token)
    ]);
}

async function loadPurchasedTickets(userId, token) {
    const status = document.getElementById('tickets-status');
    const list = document.getElementById('my-tickets');
    list.replaceChildren();
    status.textContent = 'Cargando tus entradas...';

    try {
        const tickets = await requestApiFrom(
            API_BASES_ENTRADAS,
            `/api/entradas/usuarios/${userId}`,
            {
                headers: { Authorization: 'Bearer ' + token }
            },
            '/api/entradas'
        );

        if (tickets.length === 0) {
            status.textContent = 'Todavía no tienes entradas compradas.';
            return;
        }

        status.textContent = `${tickets.length} entrada${tickets.length === 1 ? '' : 's'} en tu cuenta.`;
        tickets.forEach((ticket) => {
            const item = document.createElement('li');
            const code = document.createElement('strong');
            code.textContent = ticket.codigo;
            const type = document.createElement('span');
            type.textContent = formatTicketType(ticket.tipoEntrada);
            const dates = document.createElement('small');
            dates.textContent = `${formatDate(ticket.fechaInicioValidez)} – ${formatDate(ticket.fechaFinValidez)} · ${ticket.estado}`;
            item.append(code, type, dates);
            list.append(item);
        });
    } catch (error) {
        status.textContent = error.message;
    }
}

async function loadWalletBalance(userId, token) {
    const status = document.getElementById('wallet-status');
    status.textContent = 'Consultando el saldo de prueba...';
    status.classList.remove('is-success');

    try {
        const result = await requestApi(`/api/usuarios/${userId}/saldo`, {
            headers: { Authorization: 'Bearer ' + token }
        });
        renderWalletBalance(result.saldo);
        status.textContent = 'Saldo de prueba listo para usar en pedidos de la tienda.';
        status.classList.add('is-success');
    } catch (error) {
        status.textContent = error.message;
    }
}

function renderWalletBalance(balance) {
    document.getElementById('wallet-balance').textContent =
        `${Number(balance).toLocaleString('es-ES', { minimumFractionDigits: 2 })} €`;
}

function formatTicketType(type) {
    return {
        vip: 'Abono VIP',
        abono_completo: 'Abono completo',
        abono_un_dia: 'Entrada de un día'
    }[type] || type;
}

function formatDate(value) {
    if (!value) {
        return 'Fecha por confirmar';
    }

    const date = new Date(`${value}T12:00:00`);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString('es-ES');
}

async function requestApi(url, options) {
    return requestApiFrom(API_BASES_USUARIOS, url, options, '/api/usuarios');
}

async function requestApiFrom(baseUrls, url, options, routePrefix) {
    let lastError;
    for (const baseUrl of baseUrls) {
        let response;
        try {
            response = await fetch(`${baseUrl}${url.replace(routePrefix, '')}`, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                }
            });
        } catch {
            continue;
        }

        let result;
        try {
            result = await response.json();
        } catch {
            lastError = new Error('El servicio devolvió una respuesta no válida.');
            continue;
        }

        if (response.status === 404 || response.status === 405) {
            continue;
        }

        if (!response.ok) {
            throw new Error(result.mensaje || 'No se pudo completar la operación.');
        }

        return result;
    }

    if (lastError) {
        throw lastError;
    }
    const serviceName = routePrefix === '/api/usuarios' ? 'usuarios' : 'entradas';
    throw new Error(`No se pudo conectar con la API de ${serviceName}. Comprueba que el servicio esté iniciado.`);
}

function readSession() {
    try {
        const storedSession = sessionStorage.getItem(CLAVE_SESION);
        return storedSession ? JSON.parse(storedSession) : null;
    } catch {
        return null;
    }
}
