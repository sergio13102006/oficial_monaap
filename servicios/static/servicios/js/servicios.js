const INPUT_RULES = {
    alnum: {
        pattern: /[^\p{L}\p{N}\s]/gu,
        allow: (text) => /^[\p{L}\p{N}\s]*$/u.test(text),
    },
    numeric: {
        pattern: /[^\d]/g,
        allow: (text) => /^\d*$/.test(text),
    },
    money: {
        pattern: /[^\d.,\s]/g,
        allow: (text) => /^[\d.,\s]*$/.test(text),
    },
    text: {
        pattern: /[<>]/g,
        allow: (text) => !/[<>]/.test(text),
    },
};

function getServicioPageUrls() {
    const page = document.getElementById('servicios-page');
    const urls = {
        crearServicio: '',
        listaServicios: '',
        editarServicio: '',
        toggleActivo: '',
    };

    if (page) {
        urls.crearServicio = page.dataset.crearServicioUrl || '';
        urls.listaServicios = page.dataset.listaServiciosUrl || '';
        urls.editarServicio = page.dataset.editarServicioUrl || '';
        urls.toggleActivo = page.dataset.toggleActivoUrl || '';
    }

    if (window.URLS) {
        urls.crearServicio = urls.crearServicio || window.URLS.crearServicio || '';
        urls.listaServicios = urls.listaServicios || window.URLS.listaServicios || '';
        urls.editarServicio = urls.editarServicio || window.URLS.editarServicio || '';
        urls.toggleActivo = urls.toggleActivo || window.URLS.toggleActivo || '';
    }

    return urls;
}

const SERVICIOS_URLS = getServicioPageUrls();

function bindRestrictedInput(input, ruleName) {
    if (!input || input.dataset.guardWired === '1' || !INPUT_RULES[ruleName]) return;
    input.dataset.guardWired = '1';

    const rule = INPUT_RULES[ruleName];
    const sanitize = () => {
        const cleaned = String(input.value || '').replace(rule.pattern, '');
        if (cleaned !== input.value) {
            input.value = cleaned;
        }
    };

    input.addEventListener('beforeinput', function (e) {
        if (!e.inputType || !e.inputType.startsWith('insert')) return;
        if (!rule.allow(e.data || '')) e.preventDefault();
    });

    input.addEventListener('paste', function (e) {
        const pasted = e.clipboardData?.getData('text') || '';
        if (!rule.allow(pasted)) {
            e.preventDefault();
            sanitize();
        }
    });

    input.addEventListener('input', sanitize);
}

function wireServicioGuards(scope) {
    const root = scope || document;
    const fields = [
        ['[name="nombre"]', 'alnum'],
        ['[name="precio"]', 'money'],
        ['[name="descripcion"]', 'text'],
    ];

    fields.forEach(function (pair) {
        const input = root.querySelector(pair[0]) || document.querySelector(pair[0]);
        if (input) bindRestrictedInput(input, pair[1]);
    });
}

document.addEventListener('DOMContentLoaded', function () {

    // Aplicar guards también al cargar
    wireServicioGuards(document);

    // ── ESTADO DE VISTA ──
    let currentView  = 'grid';
    let currentPage  = 1;
    let itemsPerPage = parseInt(document.getElementById('gridSize')?.value || 4, 10) * 3;

    // ── TOGGLE VISTA ──
    const btnGrid = document.getElementById('btnGrid');
    const btnList = document.getElementById('btnList');

    if (btnGrid) btnGrid.addEventListener('click', () => setView('grid'));
    if (btnList) btnList.addEventListener('click', () => setView('list'));

    function setView(v) {
        currentView = v;
        const vg = document.getElementById('viewGrid');
        const vl = document.getElementById('viewList');
        if (vg) vg.style.display = v === 'grid' ? 'grid' : 'none';
        if (vl) vl.style.display = v === 'list' ? 'flex'  : 'none';
        if (btnGrid) btnGrid.classList.toggle('active', v === 'grid');
        if (btnList) btnList.classList.toggle('active', v === 'list');
        const gsw = document.getElementById('gridSizeWrap');
        if (gsw) gsw.style.display = v === 'grid' ? 'flex' : 'none';
        currentPage = 1;
        render();
    }

    // ── TAMAÑO CUADRÍCULA ──
    const gridSizeEl = document.getElementById('gridSize');
    if (gridSizeEl) {
        gridSizeEl.addEventListener('change', () => {
            const vg = document.getElementById('viewGrid');
            if (vg) vg.style.setProperty('--cols', gridSizeEl.value);
            itemsPerPage = parseInt(gridSizeEl.value, 10) * 3;
            currentPage = 1;
            render();
        });

        const vg = document.getElementById('viewGrid');
        if (vg) vg.style.setProperty('--cols', gridSizeEl.value);
        itemsPerPage = parseInt(gridSizeEl.value, 10) * 3;
    }

    // ── RENDER (paginación client-side sobre resultados actuales del DOM) ──
    function getItems() {
        if (currentView === 'grid') return Array.from(document.querySelectorAll('#viewGrid .lib-card'));
        return Array.from(document.querySelectorAll('#viewList .lib-row'));
    }

    function render() {
        const items      = getItems();
        const total      = items.length;
        const totalPages = Math.max(1, Math.ceil(total / itemsPerPage));
        if (currentPage > totalPages) currentPage = totalPages;

        const start = (currentPage - 1) * itemsPerPage;
        const end   = start + itemsPerPage;

        // Ocultar todos
        Array.from(document.querySelectorAll('#viewGrid .lib-card')).forEach(el => el.style.display = 'none');
        Array.from(document.querySelectorAll('#viewList .lib-row')).forEach(el => el.style.display = 'none');

        // Mostrar página actual
        items.slice(start, end).forEach(el => {
            el.style.display = currentView === 'grid' ? 'block' : 'flex';
        });

        const libCount = document.getElementById('libCount');
        if (libCount) {
            libCount.textContent = total > 0
                ? `Mostrando ${start + 1}–${Math.min(end, total)} de ${total}`
                : 'Sin resultados';
        }

        renderPagination(totalPages);
    }

    function renderPagination(totalPages) {
        const info = document.getElementById('pageInfo');
        const btns = document.getElementById('pageButtons');
        if (!info || !btns) return;

        info.textContent = `Página ${currentPage} de ${totalPages}`;
        btns.innerHTML   = '';

        btns.appendChild(makePageBtn('‹', currentPage === 1, () => { currentPage--; render(); }));

        for (let i = 1; i <= totalPages; i++) {
            if (totalPages > 7 && i > 2 && i < totalPages - 1 && Math.abs(i - currentPage) > 1) {
                if (i === 3 || i === totalPages - 2) {
                    const dots = document.createElement('span');
                    dots.textContent = '…';
                    dots.style.cssText = 'padding:0 4px;color:var(--text-muted);line-height:32px;';
                    btns.appendChild(dots);
                }
                continue;
            }
            const btn = makePageBtn(i, false, () => { currentPage = i; render(); });
            if (i === currentPage) btn.classList.add('active');
            btns.appendChild(btn);
        }

        btns.appendChild(makePageBtn('›', currentPage === totalPages, () => { currentPage++; render(); }));
    }

    function makePageBtn(label, disabled, onClick) {
        const btn = document.createElement('button');
        btn.className = 'lib-page-btn';
        btn.textContent = label;
        btn.disabled    = disabled;
        btn.addEventListener('click', onClick);
        return btn;
    }

    // Re-render cuando el AJAX actualiza el partial
    const resultados = document.getElementById('lista-servicios-resultados');
    if (resultados) {
        const observer = new MutationObserver(() => {
            currentPage = 1;
            render();
        });
        observer.observe(resultados, { childList: true, subtree: false });
    }

    render();

    // ── CSRF TOKEN (desde cookie, funciona en JS externo) ──
    function getCookie(name) {
        const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
        return match ? decodeURIComponent(match[2]) : '';
    }

    // ── MODAL CREAR ──
    const modalCrear = document.getElementById('modalFormServicio');
    if (modalCrear) {
        modalCrear.addEventListener('show.bs.modal', function () {
            const content = document.getElementById('modalFormContent');
            content.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary" role="status"></div><p class="mt-3">Cargando...</p></div>';
            fetch(SERVICIOS_URLS.crearServicio + '?modal=1')
                .then(r => r.text())
                .then(html => {
                    content.innerHTML = html;
                    ejecutarScripts(content);
                    window.initServicioForms && window.initServicioForms(content);
                })
                .catch(() => { content.innerHTML = '<div class="alert alert-danger m-3">Error al cargar.</div>'; });
        });
    }

    // ── MODAL EDITAR ──
    window.abrirModalEditar = function (editUrl) {
        const modal   = document.getElementById('modalEditarServicio');
        const content = document.getElementById('modalEditarContent');
        if (!modal || !content) return;

        const url = (editUrl || '').trim();
        if (!url) {
            alert('No se pudo abrir el formulario de edición.');
            return;
        }

        content.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary" role="status"></div><p class="mt-3">Cargando...</p></div>';
        const bsModal = bootstrap.Modal.getOrCreateInstance(modal);
        bsModal.show();

        fetch(`${url}?modal=1`)
            .then(r => r.text())
            .then(html => {
                content.innerHTML = html;
                ejecutarScripts(content);
                window.initServicioForms && window.initServicioForms(content);
            })
            .catch(() => { content.innerHTML = '<div class="alert alert-danger m-3">Error al cargar.</div>'; });
    };

    // ── MODAL ELIMINAR ──
    window.abrirModalEliminar = function (deleteUrl, nombre) {
        const url = (deleteUrl || '').trim();
        if (!url) {
            alert('No se pudo abrir la confirmación de eliminación.');
            return;
        }

        const label = nombre || 'este servicio';

        Swal.fire({
            title: '¿Eliminar servicio?',
            html: `¿Seguro que deseas eliminar <strong>${label}</strong>? Esta acción no se puede deshacer.`,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Sí, eliminar',
            cancelButtonText: 'Cancelar',
            confirmButtonColor: '#dc3545',
            cancelButtonColor: '#6c757d',
        }).then(result => {
            if (!result.isConfirmed) return;

            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(async response => {
                const data = await response.json().catch(() => ({}));
                if (!response.ok || !data.success) {
                    throw new Error(data.message || 'No se pudo eliminar el servicio.');
                }

                await Swal.fire({
                    title: 'Servicio eliminado',
                    text: data.message || 'El servicio fue eliminado correctamente.',
                    icon: 'success',
                    confirmButtonText: 'OK',
                    confirmButtonColor: '#4b2f2a',
                });

                window.location.reload();
            })
            .catch(err => {
                Swal.fire({
                    title: 'Error',
                    text: err.message || 'Ocurrió un error al eliminar el servicio.',
                    icon: 'error',
                    confirmButtonText: 'OK',
                    confirmButtonColor: '#dc3545',
                });
            });
        });
    };

    // ── SWITCH ACTIVO ──
    document.addEventListener('change', function (e) {
        if (!e.target.classList.contains('switch-activo')) return;

        const cb = e.target;
        const id = cb.dataset.id;
        const endpoint = cb.dataset.toggleUrl || '';

        if (!id || !endpoint) {
            cb.checked = !cb.checked;
            alert('No se pudo cambiar el estado.');
            return;
        }

        fetch(endpoint, {
            method : 'POST',
            credentials: 'same-origin',
            headers: {
                'X-CSRFToken'     : getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(async r => {
            const contentType = (r.headers.get('content-type') || '').toLowerCase();
            const payload = contentType.includes('application/json')
                ? await r.json()
                : { success: false, message: await r.text() };

            if (!r.ok && !payload.success) {
                throw new Error(payload.message || `HTTP ${r.status}`);
            }

            return payload;
        })
        .then(data => {
            if (data.success) {
                // Sincronizar ambas vistas (grid y list)
                document.querySelectorAll(`.switch-activo[data-id="${id}"]`).forEach(el => {
                    el.checked = data.activo;

                    const card = el.closest('.lib-card');
                    if (card) {
                        const badge = card.querySelector('.lib-card__status');
                        if (badge) {
                            badge.textContent = data.activo ? 'Activo' : 'Inactivo';
                            badge.className   = 'lib-card__status ' + (data.activo ? 'lib-card__status--active' : 'lib-card__status--inactive');
                        }
                        card.dataset.estado = data.activo ? 'activo' : 'inactivo';
                    }

                    const row = el.closest('.lib-row');
                    if (row) row.dataset.estado = data.activo ? 'activo' : 'inactivo';
                });
            } else {
                cb.checked = !cb.checked;
                alert(data.message || 'Error al cambiar el estado.');
            }
        })
        .catch((error) => {
            console.error('Error cambiando estado del servicio:', error);
            cb.checked = !cb.checked;
            alert(error.message || 'Error de conexión.');
        });
    });

    document.addEventListener('click', function (e) {
        const editBtn = e.target.closest('.lib-card__action-btn--edit');
        if (editBtn) {
            e.preventDefault();
            abrirModalEditar(editBtn.dataset.editUrl);
            return;
        }

        const delBtn = e.target.closest('.lib-card__action-btn--del');
        if (delBtn) {
            e.preventDefault();
            abrirModalEliminar(delBtn.dataset.deleteUrl, delBtn.dataset.nombre);
        }
    });

    document.addEventListener('submit', function (e) {
        const form = e.target && e.target.closest ? e.target.closest('#formEliminarServicio') : null;
        if (!form) return;

        e.preventDefault();
        e.stopPropagation();
        if (typeof e.stopImmediatePropagation === 'function') {
            e.stopImmediatePropagation();
        }

        if (form.dataset.eliminando === '1') return;
        form.dataset.eliminando = '1';

        const submitButton = form.querySelector('button[type="submit"]');
        const originalText = submitButton ? submitButton.innerHTML : '';

        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Eliminando...';
        }

        fetch(form.action || window.location.href, {
            method: 'POST',
            body: new FormData(form),
            credentials: 'same-origin',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(async response => {
            const contentType = (response.headers.get('content-type') || '').toLowerCase();
            const data = contentType.includes('application/json')
                ? await response.json().catch(() => ({}))
                : { success: false, message: await response.text() };

            if (!response.ok || !data.success) {
                throw new Error(data.message || 'No se pudo eliminar el servicio.');
            }

            const modalEl = form.closest('.modal') || document.getElementById('modalEliminarServicio');
            const modalInstance = modalEl ? bootstrap.Modal.getInstance(modalEl) : null;

            if (modalInstance) {
                modalInstance.hide();
            }

            await Swal.fire({
                title: 'Servicio eliminado',
                text: data.message || 'El servicio fue eliminado correctamente.',
                icon: 'success',
                confirmButtonText: 'OK',
                confirmButtonColor: '#4b2f2a',
            });

            window.location.reload();
        })
        .catch(error => {
            console.error('Error eliminando servicio:', error);
            if (typeof Swal !== 'undefined' && Swal.fire) {
                Swal.fire({
                    title: 'Error',
                    text: error.message || 'Ocurrió un error al eliminar el servicio.',
                    icon: 'error',
                    confirmButtonText: 'OK',
                    confirmButtonColor: '#dc3545',
                });
            } else {
                alert(error.message || 'Ocurrió un error al eliminar el servicio.');
            }
        })
        .finally(() => {
            delete form.dataset.eliminando;
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.innerHTML = originalText || '<i class="bi bi-trash"></i> Sí, Eliminar';
            }
        });
    }, true);

    // ── HELPER: ejecutar scripts inyectados por AJAX ──
    function ejecutarScripts(container) {
        container.querySelectorAll('script').forEach(old => {
            const s = document.createElement('script');
            if (old.src) s.src = old.src;
            else s.textContent = old.textContent;
            old.parentNode.replaceChild(s, old);
        });
    }

});

/* =========================================
   VALIDACION EN TIEMPO REAL - SERVICIOS
========================================= */
(function () {
    const CAMPOS_SERVICIO = ['nombre', 'precio', 'descripcion', 'imagen', 'video', 'activo'];

    function getCookie(name) {
        const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
        return match ? decodeURIComponent(match[2]) : '';
    }

    function getForms(scope = document) {
        return scope.querySelectorAll('#formServicio, #formServicioPage, form[data-servicio-form="1"]');
    }

    function getFieldGroup(field) {
        return field.closest('.mb-3') || field.closest('.form-check');
    }

    function ensureFieldStructure(field) {
        const group = getFieldGroup(field);
        if (!group) return null;

        if (field.type === 'checkbox') {
            let errorBox = group.querySelector('.servicio-field-error');
            if (!errorBox) {
                errorBox = document.createElement('div');
                errorBox.className = 'servicio-field-error';
                group.appendChild(errorBox);
            }
            return { group, wrapper: group, icon: null, errorBox };
        }

        let wrapper = field.parentElement;
        if (!wrapper.classList.contains('servicio-input-wrap')) {
            wrapper = document.createElement('div');
            wrapper.className = 'servicio-input-wrap';
            field.parentNode.insertBefore(wrapper, field);
            wrapper.appendChild(field);
        }

        let icon = wrapper.querySelector('.servicio-field-icon');
        if (!icon) {
            icon = document.createElement('span');
            icon.className = 'servicio-field-icon';
            wrapper.appendChild(icon);
        }

        let errorBox = group.querySelector('.servicio-field-error');

        if (!errorBox) {
            const existingError = group.querySelector('.text-danger');
            if (existingError) {
                existingError.classList.add('servicio-field-error');
                existingError.classList.remove('text-danger');
                errorBox = existingError;
            }
        }

        if (!errorBox) {
            errorBox = document.createElement('div');
            errorBox.className = 'servicio-field-error';
            wrapper.insertAdjacentElement('afterend', errorBox);
        }

        return { group, wrapper, icon, errorBox };
    }

    function clearState(field) {
        const parts = ensureFieldStructure(field);
        if (!parts) return;

        const { wrapper, icon, errorBox } = parts;

        wrapper.classList.remove('is-valid', 'is-invalid');
        field.classList.remove('servicio-valid-control', 'servicio-invalid-control');

        if (icon) icon.innerHTML = '';
        errorBox.innerHTML = '';
        errorBox.classList.remove('is-visible');
    }

    function setValid(field) {
        const parts = ensureFieldStructure(field);
        if (!parts) return;

        const { wrapper, icon, errorBox } = parts;

        wrapper.classList.remove('is-invalid');
        wrapper.classList.add('is-valid');

        field.classList.remove('servicio-invalid-control');
        field.classList.add('servicio-valid-control');

        if (icon) icon.innerHTML = '<i class="bi bi-check-lg"></i>';

        errorBox.innerHTML = '';
        errorBox.classList.remove('is-visible');
    }

    function setInvalid(field, message) {
        const parts = ensureFieldStructure(field);
        if (!parts) return;

        const { wrapper, icon, errorBox } = parts;

        wrapper.classList.remove('is-valid');
        wrapper.classList.add('is-invalid');

        field.classList.remove('servicio-valid-control');
        field.classList.add('servicio-invalid-control');

        if (icon) icon.innerHTML = '<i class="bi bi-exclamation-circle-fill"></i>';

        errorBox.innerHTML = message || 'Campo inválido.';
        errorBox.classList.add('is-visible');
    }

    function isEmptyValue(field) {
        if (field.type === 'file') {
            return !(field.files && field.files.length);
        }
        if (field.type === 'checkbox') {
            return false;
        }
        return !(field.value || '').trim();
    }

    function validateField(field, force = false) {
        if (!field || !CAMPOS_SERVICIO.includes(field.name)) return true;

        ensureFieldStructure(field);

        const touched = field.dataset.touched === '1' || force;
        const name = field.name;
        const rawValue = field.type === 'file' || field.type === 'checkbox' ? '' : (field.value || '').trim();

        let valid = true;
        let message = '';

        if (name === 'nombre') {
            if (!rawValue) {
                valid = false;
                message = 'El nombre del servicio es obligatorio.';
            } else if (field.dataset.nombreDuplicado === '1') {
                valid = false;
                message = 'Ya existe un servicio con este nombre.';
            }
        }

        if (name === 'precio') {
            if (!rawValue) {
                valid = false;
                message = 'El precio es obligatorio.';
            } else {
                const normalized = rawValue.replace(',', '.').replace(/\s+/g, '');
                if (isNaN(Number(normalized))) {
                    valid = false;
                    message = 'Ingresa un precio válido.';
                } else if (Number(normalized) < 0) {
                    valid = false;
                    message = 'El precio no puede ser negativo.';
                }
            }
        }

        if (name === 'descripcion') {
            if (!rawValue) {
                valid = false;
                message = 'La descripción es obligatoria.';
            } else if (rawValue.length < 10) {
                valid = false;
                message = 'La descripción debe tener al menos 10 caracteres.';
            }
        }

        if (name === 'activo') {
            valid = true;
        }

        if (name === 'imagen') {
            const file = field.files && field.files[0];
            if (file && file.type && !file.type.startsWith('image/')) {
                valid = false;
                message = 'Debes seleccionar un archivo de imagen válido.';
            }
        }

        if (name === 'video') {
            const file = field.files && field.files[0];
            if (file && file.type && !file.type.startsWith('video/')) {
                valid = false;
                message = 'Debes seleccionar un archivo de video válido.';
            }
        }

        // Al inicio, si el usuario no ha tocado el campo, lo dejamos neutro
        if (!touched && isEmptyValue(field)) {
            clearState(field);
            return false;
        }

        if (valid) {
            setValid(field);
        } else {
            setInvalid(field, message);
        }

        return valid;
    }

    function getServicioId(form) {
        return (form?.dataset?.servicioId || '').trim();
    }

    function wireNombreDuplicado(form) {
        const field = form.querySelector('[name="nombre"]');
        if (!field || field.dataset.nombreDupWired === '1') return;
        field.dataset.nombreDupWired = '1';

        let timer = null;
        const schedule = () => {
            clearTimeout(timer);
            timer = setTimeout(async () => {
                const value = (field.value || '').trim();
                if (!value || value.length < 2) return;

                const endpoint = (form.dataset.servicioValidarUrl || '').trim();
                if (!endpoint) return;
                const url = new URL(endpoint, window.location.origin);
                url.searchParams.set('nombre', value);
                const servicioId = getServicioId(form);
                if (servicioId) url.searchParams.set('servicio_id', servicioId);

                const token = String(Date.now()) + Math.random().toString(36).slice(2);
                field.dataset.nombreCheckToken = token;

                try {
                    const response = await fetch(url.toString(), {
                        headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    });
                    const data = await response.json().catch(() => ({}));
                    if (field.dataset.nombreCheckToken !== token) return;

                    if (!data.valid) {
                        field.dataset.nombreDuplicado = '1';
                        setInvalid(field, data.message || 'Ya existe un servicio con este nombre.');
                        return;
                    }
                    delete field.dataset.nombreDuplicado;
                    setValid(field);
                } catch (error) {
                    console.warn('No se pudo validar el nombre del servicio:', error);
                }
            }, 350);
        };

        field.addEventListener('input', schedule);
        field.addEventListener('blur', schedule);
    }

    async function validarNombreServicioAntesDeGuardar(form) {
        const field = form.querySelector('[name="nombre"]');
        if (!field) return true;

        const value = (field.value || '').trim();
        if (!value) return false;

        const endpoint = (form.dataset.servicioValidarUrl || '').trim();
        if (!endpoint) return true;

        const url = new URL(endpoint, window.location.origin);
        url.searchParams.set('nombre', value);
        const servicioId = getServicioId(form);
        if (servicioId) url.searchParams.set('servicio_id', servicioId);

        try {
            const response = await fetch(url.toString(), {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
            });
            const data = await response.json().catch(() => ({}));

            if (!data.valid) {
                field.dataset.nombreDuplicado = '1';
                field.dataset.touched = '1';
                setInvalid(field, data.message || 'Ya existe un servicio con este nombre.');
                return false;
            }

            delete field.dataset.nombreDuplicado;
            return true;
        } catch (error) {
            console.warn('No se pudo validar el nombre del servicio antes de guardar:', error);
            return true;
        }
    }

    function applyServerErrors(form, errors) {
        if (!errors) return;

        Object.keys(errors).forEach(fieldName => {
            const field = form.querySelector(`[name="${fieldName}"]`);
            if (!field) return;

            const messages = errors[fieldName];
            let firstMessage = 'Campo inválido.';

            if (Array.isArray(messages) && messages.length) {
                firstMessage = messages[0];
            } else if (typeof messages === 'string') {
                firstMessage = messages;
            }

            setInvalid(field, firstMessage);
        });
    }

    async function recargarListadoServicios() {
        const target = document.getElementById('lista-servicios-resultados');
        const filtros = document.getElementById('filtrosServicios');
        const ajaxUrl = SERVICIOS_URLS.listaServicios;

        if (!target || !ajaxUrl) {
            window.location.reload();
            return;
        }

        const params = filtros ? new URLSearchParams(new FormData(filtros)) : new URLSearchParams();
        const url = `${ajaxUrl}?${params.toString()}`;

        const response = await fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin'
        });

        if (!response.ok) {
            throw new Error(`No se pudo recargar la lista (${response.status}).`);
        }

        const html = await response.text();
        target.innerHTML = html;
    }

    function cerrarModalBootstrap(modalEl) {
        return new Promise(resolve => {
            if (!modalEl) {
                resolve();
                return;
            }

            const instance = bootstrap.Modal.getInstance(modalEl) || bootstrap.Modal.getOrCreateInstance(modalEl);
            if (!instance) {
                resolve();
                return;
            }

            let resolved = false;
            const done = () => {
                if (resolved) return;
                resolved = true;
                modalEl.removeEventListener('hidden.bs.modal', done);
                resolve();
            };

            modalEl.addEventListener('hidden.bs.modal', done, { once: true });
            instance.hide();

            setTimeout(done, 500);
        });
    }

    function clearServicioFormState(form) {
        if (!form) return;

        form.querySelectorAll('[name]').forEach(field => {
            delete field.dataset.touched;
            delete field.dataset.nombreDuplicado;

            const parts = ensureFieldStructure(field);
            if (!parts) return;

            const { wrapper, icon, errorBox } = parts;
            wrapper.classList.remove('is-valid', 'is-invalid');
            field.classList.remove('servicio-valid-control', 'servicio-invalid-control');
            if (icon) icon.innerHTML = '';
            if (errorBox) {
                errorBox.innerHTML = '';
                errorBox.classList.remove('is-visible');
            }
        });
    }

    async function submitServicioFormulario(form) {
        if (!form || form.dataset.servicioSubmitting === '1') return true;
        form.dataset.servicioSubmitting = '1';

        try {
            initServicioForms(form);
            wireServicioGuards(form);

            const nombreField = form.querySelector('[name="nombre"]');
            if (nombreField && nombreField.dataset.nombreDuplicado === '1') {
                if (typeof Swal !== 'undefined' && Swal.fire) {
                    await Swal.fire({
                        title: 'Servicio duplicado',
                        text: 'Ya existe un servicio con este nombre.',
                        icon: 'error',
                        confirmButtonText: 'OK',
                        confirmButtonColor: '#dc3545',
                    });
                } else {
                    alert('Ya existe un servicio con este nombre.');
                }
                return true;
            }

            let ok = true;
            CAMPOS_SERVICIO.forEach(name => {
                const field = form.querySelector(`[name="${name}"]`);
                if (!field) return;
                field.dataset.touched = '1';
                if (!validateField(field, true)) ok = false;
            });

            if (!ok) return true;

            const nombreValido = await validarNombreServicioAntesDeGuardar(form);
            if (!nombreValido) {
                if (typeof Swal !== 'undefined' && Swal.fire) {
                    Swal.fire({
                        title: 'Servicio duplicado',
                        text: 'Ya existe un servicio con este nombre.',
                        icon: 'error',
                        confirmButtonText: 'OK',
                        confirmButtonColor: '#dc3545',
                    });
                }
                return true;
            }

            const formData = new FormData(form);
            const requestUrl = form.action || window.location.href;
            const submitButton = form.querySelector('button[type="submit"]');
            const originalText = submitButton ? submitButton.innerHTML : 'Guardar';

            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Guardando...';
            }

            try {
                const response = await fetch(requestUrl, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': getCookie('csrftoken'),
                    }
                });

                const rawResponse = await response.text();
                let data = {};

                try {
                    data = JSON.parse(rawResponse);
                } catch (error) {
                    data = {};
                }

                const successByRedirect = response.ok && (
                    response.redirected || (response.url && requestUrl && response.url !== requestUrl)
                );

                if (data.success || successByRedirect) {
                    const successText = data.message || (form.dataset.servicioId
                        ? 'El servicio se actualizó correctamente.'
                        : 'El servicio se guardó correctamente.');
                    const modalEl = document.getElementById('modalFormServicio') || document.getElementById('modalEditarServicio');
                    const modalInstance = modalEl ? bootstrap.Modal.getInstance(modalEl) : null;
                    const isEdit = Boolean(form.dataset.servicioId);
                    const successTitle = isEdit ? 'Servicio actualizado' : 'Servicio guardado';

                    await cerrarModalBootstrap(modalEl);

                    if (!isEdit) {
                        form.reset();
                        clearServicioFormState(form);
                        wireServicioGuards(form);
                        wireNombreDuplicado(form);
                    }

                    if (typeof Swal !== 'undefined' && Swal.fire) {
                        await Swal.fire({
                            title: successTitle,
                            text: successText,
                            icon: 'success',
                            confirmButtonText: 'OK',
                            confirmButtonColor: '#4b2f2a',
                        });
                    } else {
                        alert(successText);
                    }

                    window.location.reload();
                    return true;
                }

                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.innerHTML = originalText;
                }

                if (data.errors) {
                    applyServerErrors(form, data.errors);
                    const nombreError = Array.isArray(data.errors.nombre) ? data.errors.nombre[0] : data.errors.nombre;
                    if (nombreError && /ya existe un servicio con este nombre/i.test(String(nombreError)) && typeof Swal !== 'undefined' && Swal.fire) {
                        Swal.fire({
                            title: 'Servicio duplicado',
                            text: String(nombreError),
                            icon: 'error',
                            confirmButtonText: 'OK',
                            confirmButtonColor: '#dc3545',
                        });
                        return true;
                    } else if (data.message && typeof Swal !== 'undefined' && Swal.fire) {
                        Swal.fire({
                            title: 'No se pudo guardar',
                            text: data.message,
                            icon: 'error',
                            confirmButtonText: 'OK',
                            confirmButtonColor: '#dc3545',
                        });
                        return true;
                    } else {
                        alert(data.message || 'Error al guardar el servicio. Verifica los campos.');
                        return true;
                    }
                } else {
                    const serverMessage = /ya existe un servicio con este nombre/i.test(rawResponse)
                        ? 'Ya existe un servicio con este nombre.'
                        : (data.message || 'Error al guardar el servicio. Verifica los campos.');

                    if (/ya existe un servicio con este nombre/i.test(serverMessage) && typeof Swal !== 'undefined' && Swal.fire) {
                        await Swal.fire({
                            title: 'Servicio duplicado',
                            text: serverMessage,
                            icon: 'error',
                            confirmButtonText: 'OK',
                            confirmButtonColor: '#dc3545',
                        });
                    } else {
                        alert(serverMessage);
                    }
                }
            } catch (error) {
                console.error('Error:', error);

                const submitButton = form.querySelector('button[type="submit"]');
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.innerHTML = 'Guardar';
                }

                if (typeof Swal !== 'undefined' && Swal.fire) {
                    Swal.fire({
                        title: 'Error',
                        text: 'Ocurrió un error al guardar el servicio.',
                        icon: 'error',
                        confirmButtonText: 'OK',
                        confirmButtonColor: '#dc3545',
                    });
                } else {
                    alert('Ocurrió un error al guardar el servicio.');
                }
            }
        } finally {
            const submitButton = form.querySelector('button[type="submit"]');
            if (submitButton && submitButton.disabled) {
                const isEdit = Boolean(form.dataset.servicioId);
                submitButton.disabled = false;
                submitButton.innerHTML = isEdit
                    ? '<i class="bi bi-check-circle"></i> Actualizar'
                    : '<i class="bi bi-check-circle"></i> Guardar';
            }

            delete form.dataset.servicioSubmitting;
        }

        return true;
    }

    function initServicioForms(scope = document) {
        const forms = getForms(scope);

        forms.forEach(form => {
            if (form.dataset.servicioInit === '1') return;
            form.dataset.servicioInit = '1';

            wireServicioGuards(form);
            wireNombreDuplicado(form);

            CAMPOS_SERVICIO.forEach(name => {
                const field = form.querySelector(`[name="${name}"]`);
                if (!field) return;

                ensureFieldStructure(field);

                // Si el campo ya viene con valor cargado en editar, lo valida al iniciar
                if (!isEmptyValue(field) || name === 'activo') {
                    field.dataset.touched = '1';
                    validateField(field, true);
                }

                // Si ya había error renderizado desde Django
                const group = getFieldGroup(field);
                const existingError = group ? group.querySelector('.servicio-field-error') : null;
                if (existingError && existingError.textContent.trim()) {
                    field.dataset.touched = '1';
                    setInvalid(field, existingError.innerHTML);
                }
            });
        });
    }

    document.addEventListener('submit', function (e) {
        const form = e.target && e.target.closest ? e.target.closest('#formServicio, #formServicioPage, form[data-servicio-form="1"]') : null;
        if (!form) return;

        e.preventDefault();
        e.stopPropagation();
        if (typeof e.stopImmediatePropagation === 'function') {
            e.stopImmediatePropagation();
        }

        form.dataset.servicioHandled = '1';
        submitServicioFormulario(form).finally(() => {
            delete form.dataset.servicioHandled;
        });
    }, true);

    document.addEventListener('input', function (e) {
        const field = e.target;
        if (!field.name || !CAMPOS_SERVICIO.includes(field.name)) return;
        if (!field.closest('#formServicio, #formServicioPage, form[data-servicio-form="1"]')) return;

        if (field.name === 'nombre') {
            delete field.dataset.nombreDuplicado;
        }
        field.dataset.touched = '1';
        validateField(field);
    });

    document.addEventListener('change', function (e) {
        const field = e.target;
        if (!field.name || !CAMPOS_SERVICIO.includes(field.name)) return;
        if (!field.closest('#formServicio, #formServicioPage, form[data-servicio-form="1"]')) return;

        field.dataset.touched = '1';
        validateField(field);
    });

    document.addEventListener('blur', function (e) {
        const field = e.target;
        if (!field.name || !CAMPOS_SERVICIO.includes(field.name)) return;
        if (!field.closest('#formServicio, #formServicioPage, form[data-servicio-form="1"]')) return;

        field.dataset.touched = '1';
        validateField(field);
    }, true);

    window.initServicioForms = initServicioForms;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            initServicioForms(document);
        });
    } else {
        initServicioForms(document);
    }
})();
