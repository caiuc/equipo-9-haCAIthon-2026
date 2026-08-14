// 1. Declaración de elementos del DOM
const passInput = document.getElementById('password-input');
const toggleBtn = document.getElementById('btn-toggle');
const rutInput = document.getElementById('rut-input');
const nameInput = document.getElementById('name-input');
const roleSelect = document.getElementById('role-select');
const submitBtn = document.getElementById('btn-submit');

// 2. Mostrar / Ocultar contraseña
if (passInput && toggleBtn) {
    toggleBtn.addEventListener('click', () => {
        const isPassword = passInput.type === 'password';
        passInput.type = isPassword ? 'text' : 'password';
        toggleBtn.textContent = isPassword ? '🙈' : '👁️';
    });
}

// 3. Capturar y guardar valores
if (submitBtn) {
    submitBtn.addEventListener('click', () => {
        const rut = rutInput ? rutInput.value.trim() : '';
        const password = passInput ? passInput.value : '';
        const fullName = nameInput ? nameInput.value.trim() : '';
        const rol = roleSelect ? roleSelect.value : '';

        const formData = {
            rut: rut,
            password: password,
            fullName: fullName,
            rol: rol
        };

        console.log('Datos guardados en variables:', formData);
        alert("¡Datos guardados correctamente!");
    });
}