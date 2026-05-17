document.addEventListener('DOMContentLoaded', function () {
    function getCookie(name) {
        const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
        return match ? decodeURIComponent(match[2]) : '';
    }

    function getCSRFToken() {
        const hiddenToken = document.querySelector('[name=csrfmiddlewaretoken]');
        if (hiddenToken && hiddenToken.value) {
            return hiddenToken.value;
        }
        return getCookie('csrftoken');
    }
    /* =========================================================
       UTILIDADES
    ========================================================= */
    const RULES = {
        numeric: {
            pattern: /[^\d]/g,
            allow: (text) => /^\d*$/.test(text),
        },
        alpha: {
            pattern: /[^\p{L}\s]/gu,
            allow: (text) => /^[\p{L}\s]*$/u.test(text),
        },
        text: {
            pattern: /[<>]/g,
            allow: (text) => !/[<>]/.test(text),
        },
        email: {
            pattern: /[^A-Za-z0-9@._-]/g,
            allow: (text) => /^[A-Za-z0-9@._-]*$/.test(text),
        },
    };

    function setButtonState(button, enabled) {
        if (!button) return;

        button.disabled = !enabled;

        if (enabled) {
            button.classList.remove('btn-secondary');
            button.classList.add('btn-dark');
        } else {
            button.classList.remove('btn-dark');
            button.classList.add('btn-secondary');
        }
    }

    function invalido(input, mensaje) {
        if (!input) return;

        input.classList.add('is-invalid');
        input.classList.remove('is-valid');

        const feedback = input.nextElementSibling;
        if (feedback) feedback.textContent = mensaje || '';
    }

    function valido(input) {
        if (!input) return;

        input.classList.remove('is-invalid');
        input.classList.add('is-valid');

        const feedback = input.nextElementSibling;
        if (feedback) feedback.textContent = '';
    }

    function limpiar(input) {
        if (!input) return;

        input.classList.remove('is-invalid', 'is-valid');

        const feedback = input.nextElementSibling;
        if (feedback) feedback.textContent = '';
    }

    function limpiarFormulario(form) {
        if (!form) return;

        form.reset();

        form.querySelectorAll('input, select, textarea').forEach(el => {
            el.classList.remove('is-valid', 'is-invalid');
            const feedback = el.nextElementSibling;
            if (feedback) feedback.textContent = '';
        });
    }

    function sanitizeValueByRule(input, rule) {
        if (!input || !rule || !RULES[rule]) return;
        const cleaned = String(input.value || '').replace(RULES[rule].pattern, '');
        if (cleaned !== input.value) {
            input.value = cleaned;
        }
    }

    function wireInputGuards(root) {
        if (!root) return;

        const selectors = [
            '#numero_documento',
            '#nombre',
            '#apellido',
            '#telefono',
            '#correo',
            '#editar_numero_documento',
            '#editar_nombre',
            '#editar_apellido',
            '#editar_telefono',
            '#editar_correo',
            '#numero_documento_legacy',
            '#nombre_legacy',
            '#apellido_legacy',
            '#correo_legacy'
        ];

        selectors.forEach(function(selector) {
            const input = root.querySelector(selector) || document.querySelector(selector);
            if (!input || input.dataset.guardWired === '1') return;
            input.dataset.guardWired = '1';

            const rule =
                input.id.includes('numero_documento') || input.id.includes('telefono')
                    ? 'numeric'
                    : input.id.includes('nombre') || input.id.includes('apellido')
                        ? 'alpha'
                        : input.id.includes('correo')
                            ? 'email'
                        : 'text';

            input.addEventListener('beforeinput', function(e) {
                if (!e.inputType || !e.inputType.startsWith('insert')) return;
                const data = e.data || '';
                if (!RULES[rule].allow(data)) {
                    e.preventDefault();
                }
            });

            input.addEventListener('paste', function(e) {
                const pasted = e.clipboardData?.getData('text') || '';
                if (!RULES[rule].allow(pasted)) {
                    e.preventDefault();
                    sanitizeValueByRule(input, rule);
                }
            });

            input.addEventListener('input', function() {
                sanitizeValueByRule(input, rule);
            });
        });
    }

    /* =========================================================
       INICIALIZADOR FORMULARIO CLIENTE CON VALIDACIÓN EN TIEMPO REAL
    ========================================================= */
    function initClienteForm(config) {
        const modal = document.getElementById(config.modalId);
        const form = document.getElementById(config.formId);
        const btnGuardar = document.getElementById(config.buttonId);

        if (!modal || !form || !btnGuardar) return;

        const obligatorios = config.requiredIds;
        const opcionales = config.optionalIds;

        const tipoDocumento = document.getElementById(config.fields.tipoDocumento);
        const numeroDocumento = document.getElementById(config.fields.numeroDocumento);
        const nombre = document.getElementById(config.fields.nombre);
        const apellido = document.getElementById(config.fields.apellido);
        const fechaNacimiento = document.getElementById(config.fields.fechaNacimiento);
        const telefono = document.getElementById(config.fields.telefono);
        const correo = document.getElementById(config.fields.correo);

        setButtonState(btnGuardar, false);
        wireInputGuards(form);

        function esCampoValido(input) {
            if (!input) return false;

            const id = input.id;
            const valor = (input.value || '').trim();
            const esObligatorio = obligatorios.includes(id);

            if (!esObligatorio && valor === '') return true;
            if (esObligatorio && valor === '') return false;

            if (id === config.fields.tipoDocumento) {
                return valor !== '';
            }

            if (id === config.fields.numeroDocumento) {
                return /^\d{6,12}$/.test(valor) &&
                    input.classList.contains('is-valid') &&
                    !input.classList.contains('is-invalid');
            }

            if (id === config.fields.nombre || id === config.fields.apellido) {
                return /^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$/.test(valor);
            }

            if (id === config.fields.fechaNacimiento) {
                const fecha = new Date(input.value + 'T00:00:00');
                const hoy = new Date();
                hoy.setHours(0, 0, 0, 0);
                return fecha <= hoy;
            }

            if (id === config.fields.telefono) {
                return /^\d{10}$/.test(valor);
            }

            if (id === config.fields.correo) {
                return /^[A-Za-z0-9._-]+@[A-Za-z0-9._-]+\.[A-Za-z]{2,}$/.test(valor);
            }

            return true;
        }

        function actualizarEstadoBoton() {
            const obligatoriosValidos = obligatorios.every(id => {
                const campo = document.getElementById(id);
                return esCampoValido(campo);
            });

            const opcionalesValidos = opcionales.every(id => {
                const campo = document.getElementById(id);
                if (!campo) return true;

                const valor = (campo.value || '').trim();
                if (valor === '') return true;

                return esCampoValido(campo);
            });

            setButtonState(btnGuardar, obligatoriosValidos && opcionalesValidos);
        }

        function validarNombreApellido(input) {
            const valor = (input.value || '').trim();
            const regex = /^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$/;

            if (!valor) {
                invalido(input, 'Campo obligatorio.');
            } else if (!regex.test(valor)) {
                invalido(input, 'Solo letras.');
            } else {
                valido(input);
            }

            actualizarEstadoBoton();
        }

        function validarTelefono(input) {
            const valor = (input.value || '').trim();

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

        function validarCorreo(input) {
            const valor = (input.value || '').trim();
            const emailRegex = /^[A-Za-z0-9._-]+@[A-Za-z0-9._-]+\.[A-Za-z]{2,}$/;

            if (!valor) {
                limpiar(input);
            } else if (!emailRegex.test(valor)) {
                invalido(input, 'Correo inválido.');
            } else {
                valido(input);
            }

            actualizarEstadoBoton();
        }

        function validarTipoDocumento(input) {
            const valor = (input.value || '').trim();

            if (!valor) {
                limpiar(input);
            } else {
                valido(input);
            }

            actualizarEstadoBoton();
        }

        function validarFechaNacimiento(input) {
            const valor = input.value;

            if (!valor) {
                limpiar(input);
                actualizarEstadoBoton();
                return;
            }

            const fechaSeleccionada = new Date(valor + 'T00:00:00');
            const hoy = new Date();
            hoy.setHours(0, 0, 0, 0);

            if (fechaSeleccionada > hoy) {
                invalido(input, 'No puede ser futura.');
            } else {
                valido(input);
            }

            actualizarEstadoBoton();
        }

        let docTimer = null;
        let docAbort = null;

        function validarDocumentoEnVivo(input) {
            const valor = (input.value || '').trim();

            if (docTimer) clearTimeout(docTimer);
            if (docAbort) docAbort.abort();

            if (!valor) {
                limpiar(input);
                actualizarEstadoBoton();
                return;
            }

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

            docAbort = new AbortController();

            docTimer = setTimeout(async () => {
                try {
                    const res = await fetch(`/clientes/validar-documento/?numero=${encodeURIComponent(valor)}`, {
                        signal: docAbort.signal
                    });

                    const data = await res.json();

                    if (!data.valido) {
                        invalido(input, data.mensaje);
                    } else {
                        valido(input);
                    }
                } catch (e) {
                    if (e.name !== 'AbortError') {
                        invalido(input, 'Error validando documento.');
                    }
                }

                actualizarEstadoBoton();
            }, 300);
        }

        // Validación EN TIEMPO REAL
        form.addEventListener('input', function (e) {
            const input = e.target;
            if (!input || !input.id) return;

            if (input.id === config.fields.numeroDocumento) {
                validarDocumentoEnVivo(input);
                return;
            }

            if (input.id === config.fields.nombre || input.id === config.fields.apellido) {
                validarNombreApellido(input);
                return;
            }

            if (input.id === config.fields.telefono) {
                validarTelefono(input);
                return;
            }

            if (input.id === config.fields.correo) {
                validarCorreo(input);
                return;
            }
        });

        // Validación por cambio
        form.addEventListener('change', function (e) {
            const input = e.target;
            if (!input || !input.id) return;

            if (input.id === config.fields.tipoDocumento) {
                validarTipoDocumento(input);
                return;
            }

            if (input.id === config.fields.fechaNacimiento) {
                validarFechaNacimiento(input);
                return;
            }

            if (input.id === config.fields.numeroDocumento) {
                validarDocumentoEnVivo(input);
                return;
            }

            if (input.id === config.fields.telefono) {
                validarTelefono(input);
                return;
            }

            if (input.id === config.fields.correo) {
                validarCorreo(input);
                return;
            }
        });

        // Validación al salir del campo
        form.addEventListener('blur', function (e) {
            const input = e.target;
            if (!input || !input.id) return;

            if (input.id === config.fields.nombre || input.id === config.fields.apellido) {
                validarNombreApellido(input);
                return;
            }

            if (input.id === config.fields.tipoDocumento) {
                validarTipoDocumento(input);
                return;
            }

            if (input.id === config.fields.fechaNacimiento) {
                validarFechaNacimiento(input);
                return;
            }

            if (input.id === config.fields.telefono) {
                validarTelefono(input);
                return;
            }

            if (input.id === config.fields.correo) {
                validarCorreo(input);
                return;
            }

            if (input.id === config.fields.numeroDocumento) {
                validarDocumentoEnVivo(input);
                return;
            }
        }, true);

        form.addEventListener('submit', async function (e) {
            e.preventDefault();

            btnGuardar.disabled = true;
            btnGuardar.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Guardando...';

            const formData = new FormData(form);

            try {
                const response = await fetch('/clientes/crear/', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });

                const data = await response.json();

                if (data.success) {
                    const selectClienteGestion = document.getElementById('selectCliente');

                    if (selectClienteGestion) {
                        const option = document.createElement('option');
                        option.value = data.cliente.id;
                        option.textContent = `${data.cliente.nombre} ${data.cliente.apellido} - ${data.cliente.numero_documento}`;
                        option.setAttribute('data-documento', data.cliente.numero_documento);
                        option.selected = true;
                        selectClienteGestion.appendChild(option);
                        selectClienteGestion.dispatchEvent(new Event('change'));
                    }

                    const modalInstance = bootstrap.Modal.getInstance(modal);
                    if (modalInstance) {
                        modalInstance.hide();
                    }

                    limpiarFormulario(form);

                    const alertaErrores = document.getElementById(config.errorAlertId);
                    if (alertaErrores) alertaErrores.classList.add('d-none');

                    const listaErrores = document.getElementById(config.errorListId);
                    if (listaErrores) listaErrores.innerHTML = '';

                    await Swal.fire({
                        title: 'Cliente guardado',
                        text: 'El cliente se guardó correctamente.',
                        icon: 'success',
                        confirmButtonColor: '#634c40',
                        confirmButtonText: 'Aceptar'
                    });

                    location.reload();
                } else {
                    const alertaErrores = document.getElementById(config.errorAlertId);
                    const listaErrores = document.getElementById(config.errorListId);

                    if (listaErrores) listaErrores.innerHTML = '';

                    if (data.errores && listaErrores) {
                        for (const [campo, mensaje] of Object.entries(data.errores)) {
                            const li = document.createElement('li');
                            li.innerHTML = `<strong>${campo}:</strong> ${mensaje}`;
                            listaErrores.appendChild(li);
                        }
                    }

                    if (alertaErrores) alertaErrores.classList.remove('d-none');
                }
            } catch (error) {
                Swal.fire({
                    title: 'Error',
                    text: 'Error al guardar el cliente. Por favor, intenta nuevamente.',
                    icon: 'error',
                    confirmButtonColor: '#634c40',
                    confirmButtonText: 'Aceptar'
                });
            } finally {
                btnGuardar.innerHTML = config.submitText || 'Guardar cliente';
                actualizarEstadoBoton();
            }
        });

        modal.addEventListener('shown.bs.modal', function () {
            setButtonState(btnGuardar, false);
            actualizarEstadoBoton();
        });

        modal.addEventListener('hidden.bs.modal', function () {
            limpiarFormulario(form);

            const alertaErrores = document.getElementById(config.errorAlertId);
            if (alertaErrores) alertaErrores.classList.add('d-none');

            const listaErrores = document.getElementById(config.errorListId);
            if (listaErrores) listaErrores.innerHTML = '';

            setButtonState(btnGuardar, false);
        });
    }

    /* =========================================================
       FORMULARIO PRINCIPAL DE CLIENTES
    ========================================================= */
    initClienteForm({
        modalId: 'modalCrearCliente',
        formId: 'formCrearCliente',
        buttonId: 'btnGuardarCliente',
        submitText: 'Guardar cliente',
        errorAlertId: 'alertaErroresCliente',
        errorListId: 'listaErroresCliente',
        requiredIds: [
            'tipo_documento',
            'numero_documento',
            'nombre',
            'apellido',
            'fecha_nacimiento'
        ],
        optionalIds: [
            'telefono',
            'correo'
        ],
        fields: {
            tipoDocumento: 'tipo_documento',
            numeroDocumento: 'numero_documento',
            nombre: 'nombre',
            apellido: 'apellido',
            fechaNacimiento: 'fecha_nacimiento',
            telefono: 'telefono',
            correo: 'correo'
        }
    });

    /* =========================================================
       FORMULARIO CLIENTE DENTRO DE GESTIÓN DE ALISADOS
    ========================================================= */
    initClienteForm({
        modalId: 'modalCrearCliente',
        formId: 'formCrearClienteModal',
        buttonId: 'btnGuardarClienteModalGestion',
        submitText: 'Guardar cliente',
        errorAlertId: 'alertaErroresClienteModal',
        errorListId: 'listaErroresClienteModal',
        requiredIds: [
            'tipo_documento_cliente_modal',
            'numero_documento_cliente_modal',
            'nombre_cliente_modal',
            'apellido_cliente_modal',
            'fecha_nacimiento_cliente_modal'
        ],
        optionalIds: [
            'telefono_cliente_modal',
            'correo_cliente_modal'
        ],
        fields: {
            tipoDocumento: 'tipo_documento_cliente_modal',
            numeroDocumento: 'numero_documento_cliente_modal',
            nombre: 'nombre_cliente_modal',
            apellido: 'apellido_cliente_modal',
            fechaNacimiento: 'fecha_nacimiento_cliente_modal',
            telefono: 'telefono_cliente_modal',
            correo: 'correo_cliente_modal'
        }
    });

    /* =========================================================
       CONFIRMAR GESTIÓN DE ALISADOS DESDE CLIENTES
    ========================================================= */
    const formEditarCliente = document.getElementById('formEditarCliente');
    const btnGuardarEditar = document.getElementById('btnGuardarEditar');
    const modalEditarCliente = document.getElementById('modalEditarCliente');
    const editarCampos = {
        tipo_documento: document.getElementById('editar_tipo_documento'),
        numero_documento: document.getElementById('editar_numero_documento'),
        nombre: document.getElementById('editar_nombre'),
        apellido: document.getElementById('editar_apellido'),
        fecha_nacimiento: document.getElementById('editar_fecha_nacimiento'),
        telefono: document.getElementById('editar_telefono'),
        correo: document.getElementById('editar_correo'),
        estado: document.getElementById('editar_estado')
    };

    function asegurarWrapEditar(campo) {
        if (!campo || campo.dataset.wrapValidacion === '1') return;
        if (campo.parentElement && campo.parentElement.classList.contains('cliente-input-wrap')) {
            campo.dataset.wrapValidacion = '1';
            return;
        }

        const wrap = document.createElement('div');
        wrap.className = 'cliente-input-wrap';
        campo.parentNode.insertBefore(wrap, campo);
        wrap.appendChild(campo);

        const validIcon = document.createElement('span');
        validIcon.className = 'cliente-valid-icon';
        validIcon.innerHTML = '<i class="bi bi-check-lg"></i>';

        const invalidIcon = document.createElement('span');
        invalidIcon.className = 'cliente-invalid-icon';
        invalidIcon.innerHTML = '<i class="bi bi-exclamation-circle-fill"></i>';

        wrap.appendChild(validIcon);
        wrap.appendChild(invalidIcon);
        campo.dataset.wrapValidacion = '1';
    }

    function actualizarIconosEditar(campo, estado) {
        if (!campo) return;
        const wrap = campo.closest('.cliente-input-wrap');
        if (!wrap) return;

        wrap.classList.remove('is-ok', 'is-error');
        campo.classList.remove('is-valid', 'is-invalid');

        if (estado === 'ok') {
            wrap.classList.add('is-ok');
            campo.classList.add('is-valid');
        } else if (estado === 'error') {
            wrap.classList.add('is-error');
            campo.classList.add('is-invalid');
        }
    }

    function limpiarIconosEditar(campo) {
        if (!campo) return;
        const wrap = campo.closest('.cliente-input-wrap');
        if (wrap) wrap.classList.remove('is-ok', 'is-error');
        campo.classList.remove('is-valid', 'is-invalid');
    }

    function validarCampoEditar(campo) {
        if (!campo) return true;

        const valor = (campo.value || '').trim();
        const id = campo.id;

        if (!valor && ['editar_telefono', 'editar_correo'].includes(id)) {
            limpiarIconosEditar(campo);
            return true;
        }

        if (id === 'editar_tipo_documento') {
            if (!valor) {
                actualizarIconosEditar(campo, 'error');
                return false;
            }
            actualizarIconosEditar(campo, 'ok');
            return true;
        }

        if (id === 'editar_numero_documento') {
            const ok = /^\d{6,12}$/.test(valor);
            actualizarIconosEditar(campo, ok ? 'ok' : 'error');
            return ok;
        }

        if (id === 'editar_nombre' || id === 'editar_apellido') {
            const ok = /^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$/.test(valor);
            actualizarIconosEditar(campo, ok ? 'ok' : 'error');
            return ok;
        }

        if (id === 'editar_fecha_nacimiento') {
            if (!valor) {
                actualizarIconosEditar(campo, 'error');
                return false;
            }
            const fecha = new Date(campo.value + 'T00:00:00');
            const hoy = new Date();
            hoy.setHours(0, 0, 0, 0);
            const ok = fecha <= hoy;
            actualizarIconosEditar(campo, ok ? 'ok' : 'error');
            return ok;
        }

        if (id === 'editar_telefono') {
            const ok = /^\d{10}$/.test(valor);
            actualizarIconosEditar(campo, ok ? 'ok' : 'error');
            return ok;
        }

        if (id === 'editar_correo') {
            const ok = /^[A-Za-z0-9._-]+@[A-Za-z0-9._-]+\.[A-Za-z]{2,}$/.test(valor);
            actualizarIconosEditar(campo, ok ? 'ok' : 'error');
            return ok;
        }

        if (id === 'editar_estado') {
            actualizarIconosEditar(campo, valor ? 'ok' : 'error');
            return !!valor;
        }

        return true;
    }

    function validarFormularioEditarTiempoReal() {
        return Object.values(editarCampos).every(function(campo) {
            return validarCampoEditar(campo);
        });
    }

    if (formEditarCliente && btnGuardarEditar && modalEditarCliente) {
        Object.values(editarCampos).forEach(asegurarWrapEditar);

        formEditarCliente.addEventListener('input', function (e) {
            const campo = e.target;
            if (!campo || !campo.id || !campo.closest('#formEditarCliente')) return;
            validarCampoEditar(campo);
        });

        formEditarCliente.addEventListener('change', function (e) {
            const campo = e.target;
            if (!campo || !campo.id || !campo.closest('#formEditarCliente')) return;
            validarCampoEditar(campo);
        });

        formEditarCliente.addEventListener('blur', function (e) {
            const campo = e.target;
            if (!campo || !campo.id || !campo.closest('#formEditarCliente')) return;
            validarCampoEditar(campo);
        }, true);

        modalEditarCliente.addEventListener('shown.bs.modal', function () {
            Object.values(editarCampos).forEach(asegurarWrapEditar);
            Object.values(editarCampos).forEach(validarCampoEditar);
        });

        modalEditarCliente.addEventListener('hidden.bs.modal', function () {
            Object.values(editarCampos).forEach(function (campo) {
                if (!campo) return;
                limpiarIconosEditar(campo);
            });

            const alertaErrores = document.getElementById('alertaErroresEditar');
            const listaErrores = document.getElementById('listaErroresEditar');
            if (alertaErrores) alertaErrores.classList.add('d-none');
            if (listaErrores) listaErrores.innerHTML = '';
        });

        btnGuardarEditar.addEventListener('click', async function () {
            const url = document.getElementById('editarClienteUrl')?.value;
            if (!url) {
                Swal.fire({
                    title: 'Error',
                    text: 'No se encontró la URL de edición del cliente.',
                    icon: 'error',
                    confirmButtonColor: '#634c40',
                    confirmButtonText: 'Aceptar'
                });
                return;
            }

            const formData = new FormData(formEditarCliente);
            const btn = btnGuardarEditar;

            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Guardando...';

            try {
                const response = await fetch(url, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });

                const data = await response.json().catch(() => ({}));

                if (!response.ok || !data.success) {
                    const listaErrores = document.getElementById('listaErroresEditar');
                    const alertaErrores = document.getElementById('alertaErroresEditar');

                    if (listaErrores) {
                        listaErrores.innerHTML = '';
                        const errores = data.errores || {};
                        Object.entries(errores).forEach(([campo, mensaje]) => {
                            const li = document.createElement('li');
                            li.innerHTML = `<strong>${campo}:</strong> ${mensaje}`;
                            listaErrores.appendChild(li);
                        });
                    }

                    if (alertaErrores) {
                        alertaErrores.classList.remove('d-none');
                    }
                    return;
                }

                const modalInstance = bootstrap.Modal.getInstance(modalEditarCliente);
                if (modalInstance) modalInstance.hide();

                await Swal.fire({
                    title: 'Cliente actualizado',
                    text: 'Los cambios se guardaron correctamente.',
                    icon: 'success',
                    confirmButtonColor: '#634c40',
                    confirmButtonText: 'Aceptar'
                });

                location.reload();
            } catch (error) {
                Swal.fire({
                    title: 'Error',
                    text: 'No se pudo actualizar el cliente.',
                    icon: 'error',
                    confirmButtonColor: '#634c40',
                    confirmButtonText: 'Aceptar'
                });
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-save me-1"></i> Guardar cambios';
            }
        });
    }

    if (window.mostrarModalGestion) {
        const modalConfirmacionEl = document.getElementById('modalGestionDatos');
        const btnAbrirGestion = document.getElementById('btnAbrirGestionDesdeCliente');
        const contenedor = document.getElementById('contenedorGestionAlisadoModal');
        const modalGestionEl = document.getElementById('modalGestionAlisadoCliente');

        if (modalConfirmacionEl) {
            const modalConfirmacion = new bootstrap.Modal(modalConfirmacionEl);
            modalConfirmacion.show();
        }

        if (btnAbrirGestion && contenedor && modalGestionEl) {
            btnAbrirGestion.addEventListener('click', async function () {
                try {
                    if (!window.urlGestionModal) {
                        console.error('window.urlGestionModal no está definida');
                        alert('No se encontró la URL del formulario de gestión.');
                        return;
                    }

                    const url = `${window.urlGestionModal}?cliente=${window.clienteCreadoId}&desde_clientes=1`;

                    const response = await fetch(url, {
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest'
                        }
                    });

                    const html = await response.text();
                    contenedor.innerHTML = html;

                    // Ejecutar scripts del formulario cargado dinámicamente
                    contenedor.querySelectorAll('script').forEach(oldScript => {
                        const newScript = document.createElement('script');

                        if (oldScript.src) {
                            newScript.src = oldScript.src;
                        } else {
                            newScript.textContent = oldScript.textContent;
                        }

                        document.body.appendChild(newScript);
                        oldScript.remove();
                    });

                    const modalConfirmacion = bootstrap.Modal.getInstance(modalConfirmacionEl);
                    if (modalConfirmacion) {
                        modalConfirmacion.hide();
                    }

                    const modalGestion = new bootstrap.Modal(modalGestionEl);
                    modalGestion.show();

                } catch (error) {
                    console.error('Error cargando formulario de gestión:', error);
                    alert('No se pudo cargar el formulario.');
                }
            });
        }
    }

        document.addEventListener('change', function (e) {
        const switchInput = e.target.closest('.js-toggle-cliente-estado');
        if (!switchInput) return;

        const url = switchInput.dataset.url;
        if (!url) {
            switchInput.checked = !switchInput.checked;
            alert('No se pudo cambiar el estado.');
            return;
        }

        switchInput.disabled = true;

        fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'X-CSRFToken': getCSRFToken(),
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(async function (response) {
            const data = await response.json().catch(() => ({}));
            if (!response.ok || !data.ok) {
                throw new Error(data.mensaje || 'No se pudo cambiar el estado');
            }

            const row = switchInput.closest('tr');
            if (row) {
                const checked = data.estado === 'activo';
                const stateCell = row.querySelector('td:nth-child(5)');
                const estadoFilter = document.querySelector('select[name="estado"]');
                const filtroEstado = estadoFilter ? estadoFilter.value : '';

                if (stateCell) {
                    stateCell.innerHTML = `
                        <label class="table-switch-wrapper" title="${checked ? 'Desactivar' : 'Activar'}">
                            <input type="checkbox"
                                   class="toggle-activo-checkbox js-toggle-cliente-estado"
                                   data-url="${url}"
                                   data-nombre="${(switchInput.dataset.nombre || '').replace(/"/g, '&quot;')}"
                                   data-activo="${checked ? '1' : '0'}"
                                   ${checked ? 'checked' : ''}>
                            <span class="table-switch-slider"></span>
                        </label>
                    `;
                }

                const debeOcultarse = (!checked && filtroEstado !== 'inactivo') || (checked && filtroEstado === 'inactivo');

                await Swal.fire({
                    title: checked ? 'Cliente activado' : 'Cliente desactivado',
                    text: checked
                        ? `El cliente ${(switchInput.dataset.nombre || '').trim()} se activó correctamente.`
                        : `El cliente ${(switchInput.dataset.nombre || '').trim()} se desactivó correctamente.`,
                    icon: 'success',
                    confirmButtonColor: '#634c40',
                    confirmButtonText: 'Aceptar'
                });

                if (debeOcultarse) {
                    row.remove();
                }
            }
        })
          .catch(function (error) {
              switchInput.checked = !switchInput.checked;
              alert(error.message || 'Error al cambiar el estado');
          })
          .finally(function () {
              switchInput.disabled = false;
          });
      });

    document.addEventListener('click', async function (e) {
        const btnEditar = e.target.closest('.btn-editar-cliente');
        if (!btnEditar) return;

        e.preventDefault();

        const url = btnEditar.dataset.url || btnEditar.getAttribute('href');
        const modalEl = document.getElementById('modalEditarCliente');
        if (!url || !modalEl) return;

        try {
            const response = await fetch(url, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            const data = await response.json();
            const setValue = (id, value) => {
                const el = document.getElementById(id);
                if (el) el.value = value || '';
            };

            setValue('editar_tipo_documento', data.tipo_documento);
            setValue('editar_numero_documento', data.numero_documento);
            setValue('editar_nombre', data.nombre);
            setValue('editar_apellido', data.apellido);
            setValue('editar_fecha_nacimiento', data.fecha_nacimiento);
            setValue('editar_telefono', data.telefono);
            setValue('editar_correo', data.correo);
            setValue('editar_estado', data.estado || 'activo');

            const hiddenUrl = document.getElementById('editarClienteUrl');
            if (hiddenUrl) hiddenUrl.value = url;

            bootstrap.Modal.getOrCreateInstance(modalEl).show();
        } catch (error) {
            Swal.fire({
                title: 'Error',
                text: 'No se pudo cargar el cliente para edición.',
                icon: 'error',
                confirmButtonColor: '#634c40',
                confirmButtonText: 'Aceptar'
            });
        }
    });
});

