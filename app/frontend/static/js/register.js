// 1. Declaración de todos los elementos del DOM
const passInput = document.getElementById('password-input');
const toggleBtn = document.getElementById('btn-toggle');
const rutInput = document.getElementById('rut-input');
const nameInput = document.getElementById('name-input');
const submitBtn = document.getElementById('btn-submit');

// 2. Lógica del ojo (mostrar / ocultar contraseña)
if (passInput && toggleBtn) {
    toggleBtn.addEventListener('click', () => {
        const isPassword = passInput.type === 'password';
        passInput.type = isPassword ? 'text' : 'password';
        toggleBtn.textContent = isPassword ? '🙈' : '👁️';
    });
}

// 3. Guardar valores al hacer clic en el botón
if (submitBtn) {
    submitBtn.addEventListener('click', () => {
        const rut = rutInput ? rutInput.value.trim() : '';
        const password = passInput ? passInput.value : '';
        const fullName = nameInput ? nameInput.value.trim() : '';

        const formData = {
            rut: rut,
            password: password,
            fullName: fullName
        };

        console.log('Datos guardados en variables:', formData);
        alert("¡Datos guardados correctamente!")
    });
}