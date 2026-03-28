function mostrarAlertaArchivoNoPermitido() {
    if (typeof Swal !== 'undefined') {
        Swal.fire({
            icon: 'warning',
            title: 'Archivo no permitido',
            text: 'No se permiten otros archivos que no sean PNG, GIF, JPG o JPEG.',
            confirmButtonColor: '#5d4037',
            background: '#fdfaf8',
            color: '#4b3621'
        });
        return;
    }

    alert('No se permiten otros archivos que no sean PNG, GIF, JPG o JPEG.');
}

function configurarFotoPerfil(form, previewId, containerId) {
    const input = form ? form.querySelector('input[name="foto_perfil"]') : null;
    if (!input || input.dataset.validacionFotoPerfil === '1') return;
    input.dataset.validacionFotoPerfil = '1';

    input.addEventListener('change', function (e) {
        const file = e.target.files && e.target.files[0];
        const preview = document.getElementById(previewId);
        const container = document.getElementById(containerId);
        const icon = container ? container.querySelector('i') : null;

        if (!file) {
            if (preview) {
                preview.src = '';
                preview.style.display = 'none';
            }
            if (icon) icon.style.display = 'block';
            return;
        }

        const nombre = (file.name || '').toLowerCase();
        const mime = (file.type || '').toLowerCase();
        const extValida = /\.(jpe?g|png|gif)$/.test(nombre);
        const mimeValido = ['image/jpeg', 'image/png', 'image/gif'].includes(mime);

        if (!extValida && !mimeValido) {
            e.target.value = '';
            if (preview) {
                preview.src = '';
                preview.style.display = 'none';
            }
            if (icon) icon.style.display = 'block';
            mostrarAlertaArchivoNoPermitido();
            return;
        }

        const reader = new FileReader();
        reader.onload = function (ev) {
            if (preview) {
                preview.src = ev.target.result;
                preview.style.display = 'block';
            }
            if (icon) icon.style.display = 'none';
        };
        reader.readAsDataURL(file);
    });
}

// Función para inicializar las validaciones en tiempo real
function inicializarValidacionesUsuario() {

    const form = document.getElementById('form-crear-usuario');
    const btnGuardar = document.getElementById('btnGuardarUsuario');

    if (!form || !btnGuardar) return;
    wireUsuarioInputGuards(form);
    configurarFotoPerfil(form, 'preview-foto', 'preview-foto-container');

    /* ===============================
       INICIO: BOTÓN DESHABILITADO
    =============================== */
    btnGuardar.disabled = true;
    btnGuardar.classList.remove('btn-dark');
    btnGuardar.classList.add('btn-secondary');

    /* ===============================
       FUNCIONES VISUALES
    =============================== */
    function invalido(input, mensaje) {
        input.classList.add('is-invalid');
        input.classList.remove('is-valid');
        let feedback = input.nextElementSibling;
        
        // Si el siguiente elemento no es un feedback, buscar o crear uno
        if (!feedback || !feedback.classList.contains('invalid-feedback')) {
            // Buscar si ya existe un invalid-feedback después
            feedback = input.parentElement.querySelector('.invalid-feedback');
            if (!feedback) {
                feedback = document.createElement('div');
                feedback.className = 'invalid-feedback';
                input.parentElement.appendChild(feedback);
            }
        }
        
        feedback.textContent = mensaje;
        feedback.style.display = 'block';
    }

    function valido(input) {
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
        const feedback = input.parentElement.querySelector('.invalid-feedback');
        if (feedback) {
            feedback.textContent = '';
            feedback.style.display = 'none';
        }
    }

    function limpiar(input) {
        input.classList.remove('is-invalid', 'is-valid');
        const feedback = input.parentElement.querySelector('.invalid-feedback');
        if (feedback) {
            feedback.textContent = '';
            feedback.style.display = 'none';
        }
    }

    /* ===============================
       ESTADO DEL BOTÓN
    =============================== */
    function actualizarEstadoBoton() {

        const obligatorios = [
            'tipo_documento',
            'documento',
            'email',
            'first_name',
            'last_name',
            'password1',
            'password2',
            'rol'
        ];

        let habilitar = true;

        obligatorios.forEach(id => {
            const campo = document.getElementById(id);
            if (!campo) {
                habilitar = false;
                return;
            }

            const valor = (campo.value || '').trim();

            if (valor === '') habilitar = false;
            if (!campo.classList.contains('is-valid')) habilitar = false;
            if (campo.classList.contains('is-invalid')) habilitar = false;
        });

        btnGuardar.disabled = !habilitar;

        if (btnGuardar.disabled) {
            btnGuardar.classList.remove('btn-dark');
            btnGuardar.classList.add('btn-secondary');
        } else {
            btnGuardar.classList.remove('btn-secondary');
            btnGuardar.classList.add('btn-dark');
        }
    }

    /* ===============================
       VALIDACIÓN DOCUMENTO EN VIVO
    =============================== */
    let docTimer = null;
    let docAbort = null;

    function validarDocumentoEnVivo(valor, input) {

        if (docTimer) clearTimeout(docTimer);
        if (docAbort) docAbort.abort();

        docAbort = new AbortController();

        docTimer = setTimeout(async () => {

            if (!/^\d+$/.test(valor)) {
                invalido(input, 'Solo números.');
                actualizarEstadoBoton();
                return;
            }

            const userIdEl = document.getElementById('user_id');
            const userId = userIdEl ? userIdEl.value : '';

            let url = `/auth/validar-documento/?numero=${encodeURIComponent(valor)}`;
            if (userId) {
                url += `&user_id=${encodeURIComponent(userId)}`;
            }

            try {
                const res = await fetch(url, { signal: docAbort.signal });
                
                if (!res.ok) {
                    throw new Error(`HTTP error! status: ${res.status}`);
                }
                
                const data = await res.json();

                if (!data.valido) invalido(input, data.mensaje);
                else valido(input);

            } catch (e) {
                if (e.name !== 'AbortError') {
                    console.error('Error en validación de documento:', e);
                    // Si hay un error de red, simplemente marcamos como válido para no bloquear
                    valido(input);
                }
            }

            actualizarEstadoBoton();

        }, 300);
    }

    /* ===============================
       VALIDACIÓN EMAIL EN VIVO
    =============================== */
    let emailTimer = null;
    let emailAbort = null;

    function validarEmailEnVivo(valor, input) {

        if (emailTimer) clearTimeout(emailTimer);
        if (emailAbort) emailAbort.abort();

        emailAbort = new AbortController();

        emailTimer = setTimeout(async () => {

            // Validación básica: debe contener @ y un punto después del @
            if (!valor.includes('@') || !valor.split('@')[1]?.includes('.')) {
                invalido(input, 'Correo electrónico inválido.');
                actualizarEstadoBoton();
                return;
            }

            const userIdEl = document.getElementById('user_id');
            const userId = userIdEl ? userIdEl.value : '';

            let url = `/auth/validar-email/?email=${encodeURIComponent(valor)}`;
            if (userId) {
                url += `&user_id=${encodeURIComponent(userId)}`;
            }

            try {
                const res = await fetch(url, { signal: emailAbort.signal });
                
                if (!res.ok) {
                    throw new Error(`HTTP error! status: ${res.status}`);
                }
                
                const data = await res.json();

                if (!data.valido) invalido(input, data.mensaje);
                else valido(input);

            } catch (e) {
                if (e.name !== 'AbortError') {
                    console.error('Error en validación de email:', e);
                    // Si hay un error de red, simplemente marcamos como válido para no bloquear
                    valido(input);
                }
            }

            actualizarEstadoBoton();

        }, 300);
    }

    /* ===============================
       VALIDACIÓN CONTRASEÑAS
    =============================== */
    function validarPassword(input) {
        const valor = input.value;

        if (!valor) {
            invalido(input, 'La contraseña es obligatoria.');
            return false;
        }

        if (valor.length < 8) {
            invalido(input, 'Mínimo 8 caracteres.');
            return false;
        }

        if (!/[A-Z]/.test(valor)) {
            invalido(input, 'Debe contener al menos una mayúscula.');
            return false;
        }

        if (!/[a-z]/.test(valor)) {
            invalido(input, 'Debe contener al menos una minúscula.');
            return false;
        }

        if (!/[0-9]/.test(valor)) {
            invalido(input, 'Debe contener al menos un número.');
            return false;
        }

        valido(input);
        return true;
    }

    function validarPasswordConfirmacion() {
        const password1 = document.getElementById('password1');
        const password2 = document.getElementById('password2');

        if (!password2.value) {
            limpiar(password2);
            return;
        }

        if (password1.value !== password2.value) {
            invalido(password2, 'Las contraseñas no coinciden.');
        } else {
            valido(password2);
        }
    }

    /* ===============================
       EVENTOS INPUT
    =============================== */
    form.addEventListener('input', function (e) {

        const input = e.target;
        const valor = (input.value || '').trim();

        /* DOCUMENTO */
        if (input.id === 'documento') {
            if (!valor) {
                limpiar(input);
                actualizarEstadoBoton();
                return;
            }
            validarDocumentoEnVivo(valor, input);
            return;
        }

        /* EMAIL */
        if (input.id === 'email') {
            if (!valor) {
                invalido(input, 'El correo electrónico es obligatorio.');
                actualizarEstadoBoton();
                return;
            }
            validarEmailEnVivo(valor, input);
            return;
        }

        /* NOMBRE */
        if (input.id === 'first_name') {
            const regex = /^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$/;

            if (!valor) invalido(input, 'El nombre es obligatorio.');
            else if (!regex.test(valor)) invalido(input, 'Solo letras.');
            else if (valor.length > 150) invalido(input, 'Máximo 150 caracteres.');
            else valido(input);

            actualizarEstadoBoton();
        }

        /* APELLIDO */
        if (input.id === 'last_name') {
            const regex = /^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$/;

            if (!valor) invalido(input, 'El apellido es obligatorio.');
            else if (!regex.test(valor)) invalido(input, 'Solo letras.');
            else if (valor.length > 150) invalido(input, 'Máximo 150 caracteres.');
            else valido(input);

            actualizarEstadoBoton();
        }

        /* TELÉFONO */
        if (input.id === 'telefono') {

            if (!valor) {
                limpiar(input);
            } else if (!/^\d+$/.test(valor)) {
                invalido(input, 'Solo números.');
            } else if (valor.length !== 10) {
                invalido(input, 'Debe tener 10 dígitos.');
            } else {
                valido(input);
            }

            actualizarEstadoBoton();
        }

        /* CONTRASEÑA 1 */
        if (input.id === 'password1') {
            validarPassword(input);
            // También revalidar password2 si ya tiene valor
            const password2 = document.getElementById('password2');
            if (password2 && password2.value) {
                validarPasswordConfirmacion();
            }
            actualizarEstadoBoton();
        }

        /* CONTRASEÑA 2 */
        if (input.id === 'password2') {
            validarPasswordConfirmacion();
            actualizarEstadoBoton();
        }
    });

    /* SELECT tipo documento */
    const tipoDoc = document.getElementById('tipo_documento');
    if (tipoDoc) {
        tipoDoc.addEventListener('change', function () {
            if (!this.value.trim()) limpiar(this);
            else valido(this);
            actualizarEstadoBoton();
        });
    }

    /* SELECT rol */
    const rol = document.getElementById('rol');
    if (rol) {
        rol.addEventListener('change', function () {
            if (!this.value.trim()) {
                invalido(this, 'El rol es obligatorio.');
            } else {
                valido(this);
            }
            actualizarEstadoBoton();
        });
    }

}

// ===========================================================================================
// FUNCIÓN PARA VALIDACIONES EN EL FORMULARIO DE EDITAR USUARIO
// ===========================================================================================

function inicializarValidacionesEditarUsuario() {
    const form = document.getElementById('form-editar-usuario');
    const btnGuardar = form ? form.querySelector('button[type="submit"]') : null;

    if (!form || !btnGuardar) {
        return;
    }
    wireUsuarioInputGuards(form);
    configurarFotoPerfil(form, 'preview-foto-editar', 'preview-foto-editar-container');

    /* ===============================
       INICIO: BOTÓN DESHABILITADO
    =============================== */
    btnGuardar.disabled = true;
    btnGuardar.style.opacity = '0.5';

    /* ===============================
       FUNCIONES VISUALES
    =============================== */
    function invalido(input, mensaje) {
        input.classList.add('is-invalid');
        input.classList.remove('is-valid');
        let feedback = input.nextElementSibling;
        
        // Si el siguiente elemento no es un feedback, buscar o crear uno
        if (!feedback || !feedback.classList.contains('invalid-feedback')) {
            // Buscar si ya existe un invalid-feedback después
            feedback = input.parentElement.querySelector('.invalid-feedback');
            if (!feedback) {
                feedback = document.createElement('div');
                feedback.className = 'invalid-feedback d-block';
                input.parentElement.appendChild(feedback);
            }
        }
        
        feedback.textContent = mensaje;
        feedback.style.display = 'block';
    }

    function valido(input) {
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
        const feedback = input.parentElement.querySelector('.invalid-feedback');
        if (feedback) {
            feedback.textContent = '';
            feedback.style.display = 'none';
        }
    }

    function limpiar(input) {
        input.classList.remove('is-invalid', 'is-valid');
        const feedback = input.parentElement.querySelector('.invalid-feedback');
        if (feedback) {
            feedback.textContent = '';
            feedback.style.display = 'none';
        }
    }

    /* ===============================
       ESTADO DEL BOTÓN
    =============================== */
    function actualizarEstadoBoton() {
        // Campos obligatorios del formulario de editar
        const camposObligatorios = [
            { name: 'first_name', selector: 'input[name="first_name"]' },
            { name: 'last_name', selector: 'input[name="last_name"]' },
            { name: 'email', selector: 'input[name="email"]' },
            { name: 'tipo_documento', selector: 'select[name="tipo_documento"]' },
            { name: 'documento', selector: 'input[name="documento"]' }
        ];

        let habilitar = true;

        camposObligatorios.forEach(campo => {
            const elemento = form.querySelector(campo.selector);
            if (!elemento) {
                habilitar = false;
                return;
            }

            const valor = (elemento.value || '').trim();

            if (valor === '') habilitar = false;
            if (!elemento.classList.contains('is-valid')) habilitar = false;
            if (elemento.classList.contains('is-invalid')) habilitar = false;
        });

        btnGuardar.disabled = !habilitar;

        if (btnGuardar.disabled) {
            btnGuardar.style.opacity = '0.5';
        } else {
            btnGuardar.style.opacity = '1';
        }
    }

    /* ===============================
       VALIDACIÓN DOCUMENTO EN VIVO
    =============================== */
    let docTimer = null;
    let docAbort = null;

    function validarDocumentoEnVivo(valor, input) {
        if (docTimer) clearTimeout(docTimer);
        if (docAbort) docAbort.abort();

        docAbort = new AbortController();

        docTimer = setTimeout(async () => {
            if (!/^\d+$/.test(valor)) {
                invalido(input, 'Solo números.');
                actualizarEstadoBoton();
                return;
            }

            // Obtener el ID del usuario que se está editando
            const userIdInput = document.getElementById('user_id_editar');
            const userId = userIdInput ? userIdInput.value : '';

            let url = `/auth/validar-documento/?numero=${encodeURIComponent(valor)}`;
            if (userId) {
                url += `&user_id=${encodeURIComponent(userId)}`;
            }

            try {
                const res = await fetch(url, { signal: docAbort.signal });
                
                if (!res.ok) {
                    throw new Error(`HTTP error! status: ${res.status}`);
                }
                
                const data = await res.json();

                if (!data.valido) invalido(input, data.mensaje);
                else valido(input);

            } catch (e) {
                if (e.name !== 'AbortError') {
                    console.error('Error en validación de documento:', e);
                    valido(input);
                }
            }

            actualizarEstadoBoton();
        }, 300);
    }

    /* ===============================
       VALIDACIÓN EMAIL EN VIVO
    =============================== */
    let emailTimer = null;
    let emailAbort = null;

    function validarEmailEnVivo(valor, input) {
        if (emailTimer) clearTimeout(emailTimer);
        if (emailAbort) emailAbort.abort();

        emailAbort = new AbortController();

        emailTimer = setTimeout(async () => {
            if (!valor.includes('@') || !valor.split('@')[1]?.includes('.')) {
                invalido(input, 'Correo electrónico inválido.');
                actualizarEstadoBoton();
                return;
            }

            // Obtener el ID del usuario que se está editando
            const userIdInput = document.getElementById('user_id_editar');
            const userId = userIdInput ? userIdInput.value : '';

            let url = `/auth/validar-email/?email=${encodeURIComponent(valor)}`;
            if (userId) {
                url += `&user_id=${encodeURIComponent(userId)}`;
            }

            try {
                const res = await fetch(url, { signal: emailAbort.signal });
                
                if (!res.ok) {
                    throw new Error(`HTTP error! status: ${res.status}`);
                }
                
                const data = await res.json();

                if (!data.valido) invalido(input, data.mensaje);
                else valido(input);

            } catch (e) {
                if (e.name !== 'AbortError') {
                    console.error('Error en validación de email:', e);
                    valido(input);
                }
            }

            actualizarEstadoBoton();
        }, 300);
    }

    /* ===============================
       EVENTOS INPUT
    =============================== */
    form.addEventListener('input', function (e) {
        const input = e.target;
        const valor = (input.value || '').trim();

        /* DOCUMENTO */
        if (input.name === 'documento') {
            if (!valor) {
                invalido(input, 'El documento es obligatorio.');
                actualizarEstadoBoton();
                return;
            }
            validarDocumentoEnVivo(valor, input);
            return;
        }

        /* EMAIL */
        if (input.name === 'email') {
            if (!valor) {
                invalido(input, 'El correo electrónico es obligatorio.');
                actualizarEstadoBoton();
                return;
            }
            validarEmailEnVivo(valor, input);
            return;
        }

        /* NOMBRE */
        if (input.name === 'first_name') {
            const regex = /^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$/;

            if (!valor) invalido(input, 'El nombre es obligatorio.');
            else if (!regex.test(valor)) invalido(input, 'Solo letras y espacios.');
            else if (valor.length > 150) invalido(input, 'Máximo 150 caracteres.');
            else valido(input);

            actualizarEstadoBoton();
        }

        /* APELLIDO */
        if (input.name === 'last_name') {
            const regex = /^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$/;

            if (!valor) invalido(input, 'El apellido es obligatorio.');
            else if (!regex.test(valor)) invalido(input, 'Solo letras y espacios.');
            else if (valor.length > 150) invalido(input, 'Máximo 150 caracteres.');
            else valido(input);

            actualizarEstadoBoton();
        }

        /* TELÉFONO */
        if (input.name === 'telefono') {
            if (!valor) {
                limpiar(input);
            } else if (!/^\d+$/.test(valor)) {
                invalido(input, 'Solo números.');
            } else if (valor.length !== 10) {
                invalido(input, 'Debe tener 10 dígitos.');
            } else {
                valido(input);
            }

            actualizarEstadoBoton();
        }
    });

    /* SELECT tipo documento */
    const tipoDoc = form.querySelector('select[name="tipo_documento"]');
    if (tipoDoc) {
        tipoDoc.addEventListener('change', function () {
            if (!this.value.trim()) {
                invalido(this, 'El tipo de documento es obligatorio.');
            } else {
                valido(this);
            }
            actualizarEstadoBoton();
        });
    }

    /* SELECT rol */
    const rol = form.querySelector('select[name="rol"]');
    if (rol) {
        rol.addEventListener('change', function () {
            if (!this.value.trim()) {
                invalido(this, 'El rol es obligatorio.');
            } else {
                valido(this);
            }
            actualizarEstadoBoton();
        });
    }

    // Validar campos iniciales que ya tengan valores
    setTimeout(() => {
        const camposValidar = [
            { name: 'first_name', selector: 'input[name="first_name"]' },
            { name: 'last_name', selector: 'input[name="last_name"]' },
            { name: 'email', selector: 'input[name="email"]' },
            { name: 'documento', selector: 'input[name="documento"]' },
            { name: 'tipo_documento', selector: 'select[name="tipo_documento"]' }
        ];

        camposValidar.forEach(campo => {
            const elemento = form.querySelector(campo.selector);
            if (elemento && elemento.value) {
                // Disparar evento input para validar
                elemento.dispatchEvent(new Event('input', { bubbles: true }));
                
                // Para selects, disparar change
                if (elemento.tagName === 'SELECT') {
                    elemento.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }
        });
    }, 100);
}

// Inicializar al cargar la página
document.addEventListener('DOMContentLoaded', function() {
    inicializarValidacionesUsuario();
    inicializarValidacionesEditarUsuario();
});

// También exportar para poder llamarla cuando se cargue el modal dinámicamente
if (typeof window !== 'undefined') {
    window.inicializarValidacionesUsuario = inicializarValidacionesUsuario;
    window.inicializarValidacionesEditarUsuario = inicializarValidacionesEditarUsuario;
    window.inicializarValidacionesEditarUsuarioCompleto = inicializarValidacionesEditarUsuarioCompleto;
}

// ===========================================================================================
// FUNCIÓN PARA VALIDACIONES EN EL FORMULARIO DE EDITAR USUARIO (PÁGINA COMPLETA)
// ===========================================================================================

function inicializarValidacionesEditarUsuarioCompleto() {
    const form = document.getElementById('form-editar-usuario');
    const btnGuardar = document.getElementById('btnGuardarUsuarioEdit');

    if (!form || !btnGuardar) {
        return;
    }
    wireUsuarioInputGuards(form);
    configurarFotoPerfil(form, 'preview-foto-editar', 'preview-foto-editar-container');

    /* ===============================
       INICIO: BOTÓN DESHABILITADO
    =============================== */
    btnGuardar.disabled = true;
    btnGuardar.style.opacity = '0.5';

    /* ===============================
       FUNCIONES VISUALES
    =============================== */
    function invalido(input, mensaje) {
        input.classList.add('is-invalid');
        input.classList.remove('is-valid');
        let feedback = input.nextElementSibling;
        
        // Si el siguiente elemento no es un feedback, buscar o crear uno
        if (!feedback || !feedback.classList.contains('invalid-feedback')) {
            // Buscar si ya existe un invalid-feedback después
            feedback = input.parentElement.querySelector('.invalid-feedback');
            if (!feedback) {
                feedback = document.createElement('div');
                feedback.className = 'invalid-feedback d-block';
                input.parentElement.appendChild(feedback);
            }
        }
        
        feedback.textContent = mensaje;
        feedback.style.display = 'block';
    }

    function valido(input) {
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
        const feedback = input.parentElement.querySelector('.invalid-feedback');
        if (feedback) {
            feedback.textContent = '';
            feedback.style.display = 'none';
        }
    }

    function limpiar(input) {
        input.classList.remove('is-invalid', 'is-valid');
        const feedback = input.parentElement.querySelector('.invalid-feedback');
        if (feedback) {
            feedback.textContent = '';
            feedback.style.display = 'none';
        }
    }

    /* ===============================
       ESTADO DEL BOTÓN
    =============================== */
    function actualizarEstadoBoton() {
        // Campos obligatorios del formulario de editar
        const camposObligatorios = [
            { name: 'first_name', selector: 'input[name="first_name"]' },
            { name: 'last_name', selector: 'input[name="last_name"]' },
            { name: 'email', selector: 'input[name="email"]' },
            { name: 'tipo_documento', selector: 'select[name="tipo_documento"]' },
            { name: 'documento', selector: 'input[name="documento"]' },
            { name: 'rol', selector: 'select[name="rol"]' }
        ];

        let habilitar = true;

        camposObligatorios.forEach(campo => {
            const elemento = form.querySelector(campo.selector);
            if (!elemento) {
                habilitar = false;
                return;
            }

            const valor = (elemento.value || '').trim();

            if (valor === '') habilitar = false;
            if (!elemento.classList.contains('is-valid')) habilitar = false;
            if (elemento.classList.contains('is-invalid')) habilitar = false;
        });

        btnGuardar.disabled = !habilitar;

        if (btnGuardar.disabled) {
            btnGuardar.style.opacity = '0.5';
        } else {
            btnGuardar.style.opacity = '1';
        }
    }

    /* ===============================
       VALIDACIÓN DOCUMENTO EN VIVO
    =============================== */
    let docTimer = null;
    let docAbort = null;

    function validarDocumentoEnVivo(valor, input) {
        if (docTimer) clearTimeout(docTimer);
        if (docAbort) docAbort.abort();

        docAbort = new AbortController();

        docTimer = setTimeout(async () => {
            if (!/^\d+$/.test(valor)) {
                invalido(input, 'Solo números.');
                actualizarEstadoBoton();
                return;
            }

            // Obtener el ID del usuario que se está editando
            const userIdInput = document.getElementById('user_id_editar');
            const userId = userIdInput ? userIdInput.value : '';

            let url = `/auth/validar-documento/?numero=${encodeURIComponent(valor)}`;
            if (userId) {
                url += `&user_id=${encodeURIComponent(userId)}`;
            }

            try {
                const res = await fetch(url, { signal: docAbort.signal });
                
                if (!res.ok) {
                    throw new Error(`HTTP error! status: ${res.status}`);
                }
                
                const data = await res.json();

                if (!data.valido) invalido(input, data.mensaje);
                else valido(input);

            } catch (e) {
                if (e.name !== 'AbortError') {
                    console.error('Error en validación de documento:', e);
                    valido(input);
                }
            }

            actualizarEstadoBoton();
        }, 300);
    }

    /* ===============================
       VALIDACIÓN EMAIL EN VIVO
    =============================== */
    let emailTimer = null;
    let emailAbort = null;

    function validarEmailEnVivo(valor, input) {
        if (emailTimer) clearTimeout(emailTimer);
        if (emailAbort) emailAbort.abort();

        emailAbort = new AbortController();

        emailTimer = setTimeout(async () => {
            if (!valor.includes('@') || !valor.split('@')[1]?.includes('.')) {
                invalido(input, 'Correo electrónico inválido.');
                actualizarEstadoBoton();
                return;
            }

            // Obtener el ID del usuario que se está editando
            const userIdInput = document.getElementById('user_id_editar');
            const userId = userIdInput ? userIdInput.value : '';

            let url = `/auth/validar-email/?email=${encodeURIComponent(valor)}`;
            if (userId) {
                url += `&user_id=${encodeURIComponent(userId)}`;
            }

            try {
                const res = await fetch(url, { signal: emailAbort.signal });
                
                if (!res.ok) {
                    throw new Error(`HTTP error! status: ${res.status}`);
                }
                
                const data = await res.json();

                if (!data.valido) invalido(input, data.mensaje);
                else valido(input);

            } catch (e) {
                if (e.name !== 'AbortError') {
                    console.error('Error en validación de email:', e);
                    valido(input);
                }
            }

            actualizarEstadoBoton();
        }, 300);
    }

    /* ===============================
       EVENTOS INPUT
    =============================== */
    form.addEventListener('input', function (e) {
        const input = e.target;
        const valor = (input.value || '').trim();

        /* DOCUMENTO */
        if (input.name === 'documento') {
            if (!valor) {
                invalido(input, 'El documento es obligatorio.');
                actualizarEstadoBoton();
                return;
            }
            validarDocumentoEnVivo(valor, input);
            return;
        }

        /* EMAIL */
        if (input.name === 'email') {
            if (!valor) {
                invalido(input, 'El correo electrónico es obligatorio.');
                actualizarEstadoBoton();
                return;
            }
            validarEmailEnVivo(valor, input);
            return;
        }

        /* NOMBRE */
        if (input.name === 'first_name') {
            const regex = /^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$/;

            if (!valor) invalido(input, 'El nombre es obligatorio.');
            else if (!regex.test(valor)) invalido(input, 'Solo letras y espacios.');
            else if (valor.length > 150) invalido(input, 'Máximo 150 caracteres.');
            else valido(input);

            actualizarEstadoBoton();
        }

        /* APELLIDO */
        if (input.name === 'last_name') {
            const regex = /^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$/;

            if (!valor) invalido(input, 'El apellido es obligatorio.');
            else if (!regex.test(valor)) invalido(input, 'Solo letras y espacios.');
            else if (valor.length > 150) invalido(input, 'Máximo 150 caracteres.');
            else valido(input);

            actualizarEstadoBoton();
        }

        /* TELÉFONO */
        if (input.name === 'telefono') {
            if (!valor) {
                limpiar(input);
            } else if (!/^\d+$/.test(valor)) {
                invalido(input, 'Solo números.');
            } else if (valor.length !== 10) {
                invalido(input, 'Debe tener 10 dígitos.');
            } else {
                valido(input);
            }

            actualizarEstadoBoton();
        }
    });

    /* SELECT tipo documento */
    const tipoDoc = form.querySelector('select[name="tipo_documento"]');
    if (tipoDoc) {
        tipoDoc.addEventListener('change', function () {
            if (!this.value.trim()) {
                invalido(this, 'El tipo de documento es obligatorio.');
            } else {
                valido(this);
            }
            actualizarEstadoBoton();
        });
    }

    /* SELECT rol */
    const rol = form.querySelector('select[name="rol"]');
    if (rol) {
        rol.addEventListener('change', function () {
            if (!this.value.trim()) {
                invalido(this, 'El rol es obligatorio.');
            } else {
                valido(this);
            }
            actualizarEstadoBoton();
        });
    }

    // Validar campos iniciales que ya tengan valores
    setTimeout(() => {
        const camposValidar = [
            { name: 'first_name', selector: 'input[name="first_name"]' },
            { name: 'last_name', selector: 'input[name="last_name"]' },
            { name: 'email', selector: 'input[name="email"]' },
            { name: 'documento', selector: 'input[name="documento"]' },
            { name: 'tipo_documento', selector: 'select[name="tipo_documento"]' },
            { name: 'rol', selector: 'select[name="rol"]' }
        ];

        camposValidar.forEach(campo => {
            const elemento = form.querySelector(campo.selector);
            if (elemento && elemento.value) {
                // Disparar evento input para validar
                elemento.dispatchEvent(new Event('input', { bubbles: true }));
                
                // Para selects, disparar change
                if (elemento.tagName === 'SELECT') {
                    elemento.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }
        });
    }, 100);
}
const USUARIO_INPUT_RULES = {
    texto: /[A-Za-zÁÉÍÓÚáéíóúÑñ\s]/,
    numeros: /[0-9]/,
};

function sanitizeByRule(value, rule) {
    return Array.from(value || '').filter((ch) => rule.test(ch)).join('');
}

function bindRestrictedInput(input, rule, sanitizeFn) {
    if (!input || input.dataset.restrictionBound === '1') return;
    input.dataset.restrictionBound = '1';

    input.addEventListener('beforeinput', function (event) {
        if (!event.data || event.inputType?.startsWith('delete')) return;
        if (!rule.test(event.data)) {
            event.preventDefault();
        }
    });

    input.addEventListener('paste', function (event) {
        const text = event.clipboardData?.getData('text') || '';
        const clean = sanitizeFn(text);
        if (clean === text) return;
        event.preventDefault();

        const start = typeof input.selectionStart === 'number' ? input.selectionStart : input.value.length;
        const end = typeof input.selectionEnd === 'number' ? input.selectionEnd : input.value.length;
        input.value = `${input.value.slice(0, start)}${clean}${input.value.slice(end)}`;
        input.dispatchEvent(new Event('input', { bubbles: true }));
    });

    input.addEventListener('input', function () {
        const clean = sanitizeFn(input.value);
        if (clean !== input.value) {
            const cursor = typeof input.selectionStart === 'number' ? input.selectionStart : clean.length;
            input.value = clean;
            if (typeof input.setSelectionRange === 'function') {
                const pos = Math.min(cursor, clean.length);
                input.setSelectionRange(pos, pos);
            }
        }
    });
}

function wireUsuarioInputGuards(form) {
    if (!form) return;

    const documento = form.querySelector('#documento, #id_documento, input[name="documento"]');
    const firstName = form.querySelector('#first_name, #id_first_name, input[name="first_name"]');
    const lastName = form.querySelector('#last_name, #id_last_name, input[name="last_name"]');
    const telefono = form.querySelector('#telefono, #id_telefono, input[name="telefono"]');
    const whatsapp = form.querySelector('#whatsapp_key, #id_whatsapp_key, input[name="whatsapp_key"]');

    bindRestrictedInput(documento, USUARIO_INPUT_RULES.numeros, (value) => sanitizeByRule(value, USUARIO_INPUT_RULES.numeros));
    bindRestrictedInput(firstName, USUARIO_INPUT_RULES.texto, (value) => sanitizeByRule(value, USUARIO_INPUT_RULES.texto));
    bindRestrictedInput(lastName, USUARIO_INPUT_RULES.texto, (value) => sanitizeByRule(value, USUARIO_INPUT_RULES.texto));
    bindRestrictedInput(telefono, USUARIO_INPUT_RULES.numeros, (value) => sanitizeByRule(value, USUARIO_INPUT_RULES.numeros));
    bindRestrictedInput(whatsapp, USUARIO_INPUT_RULES.numeros, (value) => sanitizeByRule(value, USUARIO_INPUT_RULES.numeros));
}
