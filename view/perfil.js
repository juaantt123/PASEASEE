const API_BASES_USUARIOS = [
    window.SUBSONIC_API_URL,
    'http://localhost:8000/api/usuarios',
    'http://127.0.0.1:8081/api/usuarios',
    'http://127.0.0.1:8001/api/usuarios'
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
});

async function requestApi(url, options) {
    for (const baseUrl of API_BASES_USUARIOS) {
        let response;
        try {
            response = await fetch(`${baseUrl}${url.replace(/^\/api\/usuarios/, '')}`, {
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

    throw new Error('No se pudo conectar con la API de usuarios. Comprueba que esté iniciada en el puerto 8081 o 8001.');
}

function readSession() {
    try {
        const storedSession = sessionStorage.getItem(CLAVE_SESION);
        return storedSession ? JSON.parse(storedSession) : null;
    } catch {
        return null;
    }
}
