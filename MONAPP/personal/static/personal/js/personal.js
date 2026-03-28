// Función para inicializar las validaciones en tiempo real
function inicializarValidacionesPersonal() {

    const form = document.getElementById('form-crear-personal') || document.getElementById('form-editar-personal');
    const btnGuardar = document.getElementById('btnGuardarPersonal');

    if (!form || !btnGuardar) return;

    const esEdicion = form.id === 'form-editar-personal';
    const RULES = {
        numeric: {
            pattern: /[^\d]/g,
            allow: (text) => /^\d*$/.test(text),
        },
        alpha: {
            pattern: /[^\p{L}\s]/gu,
            allow: (text) => /^[\p{L}\s]*$/u.test(text),
        },
        alnum: {
            pattern: /[^\p{L}\p{N}\s]/gu,
            allow: (text) => /^[\p{L}\p{N}\s]*$/u.test(text),
        },
        text: {
            pattern: /[<>]/g,
            allow: (text) => !/[<>]/.test(text),
        },
    };

    function getRule(input) {
        if (!input) return null;
        const rule = (input.dataset.validate || '').trim();
        return RULES[rule] ? rule : null;
    }

    function sanitizeInput(input) {
        if (!input || input.type === 'file') return;
        const rule = getRule(input);
        if (!rule) return;
        const cleaned = String(input.value || '').replace(RULES[rule].pattern, '');
        if (cleaned !== input.value) {
            input.value = cleaned;
        }
    }

    function bindInputGuards(rootForm) {
        const inputs = rootForm.querySelectorAll('[data-validate]');
        inputs.forEach((input) => {
            if (input.dataset.guardWired === '1') return;
            input.dataset.guardWired = '1';

            input.addEventListener('beforeinput', (e) => {
                if (!e.inputType || !e.inputType.startsWith('insert')) return;
                const rule = getRule(input);
                if (!rule) return;
                const data = e.data || '';
                if (!RULES[rule].allow(data)) {
                    e.preventDefault();
                }
            });

            input.addEventListener('paste', (e) => {
                const rule = getRule(input);
                if (!rule) return;
                const pasted = e.clipboardData?.getData('text') || '';
                if (!RULES[rule].allow(pasted)) {
                    e.preventDefault();
                    sanitizeInput(input);
                }
            });

            input.addEventListener('input', () => sanitizeInput(input));
        });
    }

    /* ===============================
       INICIO: ESTADO DEL BOTÓN
    =============================== */
    if (esEdicion) {
        // En edición: botón habilitado desde el inicio
        btnGuardar.disabled = false;
        btnGuardar.classList.remove('personal-btn-secondary');
        btnGuardar.classList.add('personal-btn-dark');
    } else {
        // En creación: botón deshabilitado hasta completar campos
        btnGuardar.disabled = true;
        btnGuardar.classList.remove('personal-btn-dark');
        btnGuardar.classList.add('personal-btn-secondary');
    }

    /* ===============================
       FUNCIONES VISUALES
    =============================== */
    function getWrap(input) {
        return input?.closest('.personal-input-wrap') || null;
    }

    function getFeedback(input) {
        const group = input.closest('.personal-form-group');
        if (!group) return null;

        let feedback = group.querySelector('.personal-field-error');
        if (!feedback) {
            feedback = document.createElement('div');
            feedback.className = 'personal-field-error';
            group.appendChild(feedback);
        }
        return feedback;
    }

    function invalido(input, mensaje) {
        input.classList.add('is-invalid');
        input.classList.remove('is-valid');
        input.style.backgroundImage = 'none';

        const wrap = getWrap(input);
        if (wrap) {
            wrap.classList.remove('is-ok');
            wrap.classList.add('is-error');
        }

        const feedback = getFeedback(input);
        if (feedback) {
            feedback.textContent = mensaje;
            feedback.classList.add('is-visible');
        }
    }

    function valido(input) {
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
        input.style.backgroundImage = 'none';

        const wrap = getWrap(input);
        if (wrap) {
            wrap.classList.remove('is-error');
            wrap.classList.add('is-ok');
        }

        const feedback = getFeedback(input);
        if (feedback) {
            feedback.textContent = '';
            feedback.classList.remove('is-visible');
        }
    }

    function limpiar(input) {
        input.classList.remove('is-invalid', 'is-valid');
        input.style.backgroundImage = 'none';

        const wrap = getWrap(input);
        if (wrap) {
            wrap.classList.remove('is-ok', 'is-error');
        }

        const feedback = getFeedback(input);
        if (feedback) {
            feedback.textContent = '';
            feedback.classList.remove('is-visible');
        }
    }

    /* ===============================
       ESTADO DEL BOTÓN
    =============================== */
    // Campos que tienen validación activa (excluye checkbox oculto, csrf, etc.)
    const camposValidados = ['id_tipo_documento', 'id_numero_documento', 'id_nombres', 'id_apellidos', 'id_rol', 'id_telefono', 'id_correo'];

    function actualizarEstadoBoton() {

        if (esEdicion) {
            // En edición: habilitar siempre, deshabilitar solo si hay error en los campos validados
            let hayErrores = false;
            camposValidados.forEach(id => {
                const campo = document.getElementById(id);
                if (campo && campo.classList.contains('is-invalid')) {
                    hayErrores = true;
                }
            });
            btnGuardar.disabled = hayErrores;
        } else {
            // En creación: todos los obligatorios deben estar en verde
            const obligatorios = ['tipo_documento', 'numero_documento', 'nombres', 'apellidos', 'rol', 'telefono', 'correo'];
            let habilitar = true;

            obligatorios.forEach(id => {
                const campo = document.getElementById('id_' + id);
                if (!campo || (campo.value || '').trim() === '' || (!campo.classList.contains('is-valid') && campo.tagName !== 'SELECT') || campo.classList.contains('is-invalid')) {
                    // Nota: Los SELECT como tipo_documento y rol pueden no tener 'is-valid' si no se les ha disparado el evento change,
                    // pero verificamos que tengan valor.
                    if (campo.tagName === 'SELECT' && (campo.value || '').trim() !== '') {
                        // Es un select con valor, OK
                    } else {
                        habilitar = false;
                    }
                }
            });

            btnGuardar.disabled = !habilitar;
        }

        if (btnGuardar.disabled) {
            btnGuardar.classList.remove('personal-btn-dark');
            btnGuardar.classList.add('personal-btn-secondary');
        } else {
            btnGuardar.classList.remove('personal-btn-secondary');
            btnGuardar.classList.add('personal-btn-dark');
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
            if (valor.length < 6 || valor.length > 12) {
                invalido(input, 'Debe tener entre 6 y 12 dígitos.');
                actualizarEstadoBoton();
                return;
            }

            const personalId = form.dataset.personalId || '';
            let url = `/personal/validar-documento/?numero=${encodeURIComponent(valor)}`;
            if (personalId) url += `&personal_id=${encodeURIComponent(personalId)}`;

            try {
                const res = await fetch(url, { signal: docAbort.signal });
                const data = await res.json();
                if (!data.valido) invalido(input, data.mensaje);
                else valido(input);
            } catch (e) {
                if (e.name !== 'AbortError') invalido(input, 'Error validando documento.');
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
            if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(valor)) {
                invalido(input, 'Correo electrónico inválido.');
                actualizarEstadoBoton();
                return;
            }

            const personalId = form.dataset.personalId || '';
            let url = `/personal/validar-email/?email=${encodeURIComponent(valor)}`;
            if (personalId) url += `&personal_id=${encodeURIComponent(personalId)}`;

            try {
                const res = await fetch(url, { signal: emailAbort.signal });
                const data = await res.json();
                if (!data.valido) invalido(input, data.mensaje);
                else valido(input);
            } catch (e) {
                if (e.name !== 'AbortError') invalido(input, 'Error validando email.');
            }
            actualizarEstadoBoton();
        }, 300);
    }

    /* ===============================
       EVENTOS INPUT
    =============================== */
    bindInputGuards(form);

    form.addEventListener('input', function (e) {
        const input = e.target;
        sanitizeInput(input);
        const valor = (input.value || '').trim();

        /* DOCUMENTO */
        if (input.id === 'id_numero_documento') {
            if (!valor) { limpiar(input); actualizarEstadoBoton(); return; }
            if (valor.length < 6) {
                invalido(input, 'Mínimo 6 dígitos.');
                actualizarEstadoBoton();
                return;
            }
            if (valor.length > 12) {
                input.value = valor.substring(0, 12); // Truncar por si acaso
                valido(input);
            }
            validarDocumentoEnVivo(input.value.trim(), input);
            return;
        }

        /* NOMBRES */
        if (input.id === 'id_nombres') {
            const regex = /^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$/;
            if (!valor) invalido(input, 'Los nombres son obligatorios.');
            else if (!regex.test(valor)) invalido(input, 'Solo letras.');
            else if (valor.length > 150) invalido(input, 'Máximo 150 caracteres.');
            else valido(input);
            actualizarEstadoBoton();
        }

        /* APELLIDOS */
        if (input.id === 'id_apellidos') {
            const regex = /^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$/;
            if (!valor) invalido(input, 'Los apellidos son obligatorios.');
            else if (!regex.test(valor)) invalido(input, 'Solo letras.');
            else if (valor.length > 150) invalido(input, 'Máximo 150 caracteres.');
            else valido(input);
            actualizarEstadoBoton();
        }

        /* CORREO */
        if (input.id === 'id_correo') {
            if (!valor) { limpiar(input); actualizarEstadoBoton(); return; }
            validarEmailEnVivo(valor, input);
            return;
        }

        /* TELÉFONO */
        if (input.id === 'id_telefono') {
            if (!valor) { limpiar(input); actualizarEstadoBoton(); return; }
            if (!/^\d+$/.test(valor)) invalido(input, 'Solo números.');
            else if (valor.length < 10) {
                invalido(input, 'Debe tener 10 dígitos.');
            }
            else if (valor.length > 10) {
                input.value = valor.substring(0, 10);
                valido(input);
            }
            else valido(input);
            actualizarEstadoBoton();
        }
    });

    /* SELECT ROL */
    const rol = document.getElementById('id_rol');
    if (rol) {
        rol.addEventListener('change', function () {
            if (!this.value.trim()) invalido(this, 'El rol es obligatorio.');
            else valido(this);
            actualizarEstadoBoton();
        });
    }

    /* SELECT TIPO DOCUMENTO */
    const tipoDocumento = document.getElementById('id_tipo_documento');
    if (tipoDocumento) {
        tipoDocumento.addEventListener('change', function () {
            if (!this.value.trim()) invalido(this, 'El tipo de documento es obligatorio.');
            else valido(this);
            actualizarEstadoBoton();
        });
    }

    /* ===============================
       VALIDAR VALORES INICIALES (autofill / valores por defecto)
    =============================== */
    function validarValoresIniciales() {
        const doc = document.getElementById('id_numero_documento');
        const nombres = document.getElementById('id_nombres');
        const apellidos = document.getElementById('id_apellidos');
        const telefono = document.getElementById('id_telefono');
        const correo = document.getElementById('id_correo');

        if (tipoDocumento && (tipoDocumento.value || '').trim()) valido(tipoDocumento);
        if (rol && (rol.value || '').trim()) valido(rol);

        if (doc && (doc.value || '').trim()) {
            validarDocumentoEnVivo(String(doc.value).trim(), doc);
        }

        if (nombres && (nombres.value || '').trim()) {
            const valor = String(nombres.value).trim();
            const regex = /^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$/;
            if (!regex.test(valor)) invalido(nombres, 'Solo letras.');
            else if (valor.length > 150) invalido(nombres, 'Máximo 150 caracteres.');
            else valido(nombres);
        }

        if (apellidos && (apellidos.value || '').trim()) {
            const valor = String(apellidos.value).trim();
            const regex = /^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$/;
            if (!regex.test(valor)) invalido(apellidos, 'Solo letras.');
            else if (valor.length > 150) invalido(apellidos, 'Máximo 150 caracteres.');
            else valido(apellidos);
        }

        if (telefono && (telefono.value || '').trim()) {
            const valor = String(telefono.value).trim();
            if (!/^\d+$/.test(valor)) invalido(telefono, 'Solo números.');
            else if (valor.length < 10) invalido(telefono, 'Debe tener 10 dígitos.');
            else if (valor.length > 10) {
                telefono.value = valor.substring(0, 10);
                valido(telefono);
            } else valido(telefono);
        }

        if (correo && (correo.value || '').trim()) {
            validarEmailEnVivo(String(correo.value).trim(), correo);
        }

        actualizarEstadoBoton();
    }

    function aplicarLimitesBasicos() {
        const numeroDocumento = form.querySelector('input[name="numero_documento"]');
        if (numeroDocumento) {
            numeroDocumento.setAttribute('maxlength', '12');
            numeroDocumento.addEventListener('input', function () {
                this.value = this.value.replace(/[^0-9]/g, '').substring(0, 12);
            });
        }

        const telefono = form.querySelector('input[name="telefono"]');
        if (telefono) {
            telefono.setAttribute('maxlength', '10');
            telefono.addEventListener('input', function () {
                this.value = this.value.replace(/[^0-9]/g, '').substring(0, 10);
            });
        }
    }

    aplicarLimitesBasicos();
    setTimeout(validarValoresIniciales, 0);
}

// Inicializar al cargar la página
document.addEventListener('DOMContentLoaded', inicializarValidacionesPersonal);

// Exportar para poder llamarla cuando se cargue el modal dinámicamente
if (typeof window !== 'undefined') {
    window.inicializarValidacionesPersonal = inicializarValidacionesPersonal;
}
