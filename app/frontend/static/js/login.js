// Declaración de elementos para la contraseña
const passInput = document.getElementById('password-input');
const toggleBtn = document.getElementById('btn-toggle');

// Lógica del ojo (mostrar / ocultar contraseña)
if (passInput && toggleBtn) {
    toggleBtn.addEventListener('click', () => {
        const isPassword = passInput.type === 'password';
        passInput.type = isPassword ? 'text' : 'password';
        toggleBtn.textContent = isPassword ? '🙈' : '👁️';
    });
}// 1. Declaración de elementos del DOM
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

// 3. Captura y guardado de datos
if (loginBtn) {
    loginBtn.addEventListener('click', () => {
        const rut = rutInput ? rutInput.value.trim() : '';
        const password = passInput ? passInput.value : '';

        const credentials = {
            rut: rut,
            password: password
        };

        console.log('Credenciales ingresadas:', credentials);
        alert('¡Inicio de sesión capturado correctamente!');
    });
}