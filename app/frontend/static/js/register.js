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
}