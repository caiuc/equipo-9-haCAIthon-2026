// 1. Elementos del DOM
const passInput = document.getElementById('password-input');
const toggleBtn = document.getElementById('btn-toggle');
const rutInput = document.getElementById('rut-input');
const loginBtn = document.getElementById('btn-login');

// 2. Mostrar / Ocultar contraseña
if (passInput && toggleBtn) {
    toggleBtn.addEventListener('click', () => {
        const isPassword = passInput.type === 'password';
        passInput.type = isPassword ? 'text' : 'password';
        toggleBtn.textContent = isPassword ? '🙈' : '👁️';
    });
}

// 3. Capturar credenciales al presionar "Ingresar"
if (loginBtn) {
    loginBtn.addEventListener('click', () => {
        const rut = rutInput ? rutInput.value.trim() : '';
        const password = passInput ? passInput.value : '';

        // Objeto listo para enviar o validar
        const credentials = {
            rut: rut,
            password: password
        };

        console.log('Credenciales ingresadas:', credentials);
        alert(`Iniciando sesión con RUT: ${rut}`);
    });
}