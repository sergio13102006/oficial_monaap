(function () {
    const root = document.getElementById('personal-page');
    if (!root) return;

    const urls = {
        create: root.dataset.crearUrl || '/personal/crear/',
        list: root.dataset.listUrl || '/personal/',
    };

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i += 1) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === `${name}=`) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function showModal(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) return;
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    function hideModal(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) return;
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }

    function closeAllModals() {
        hideModal('modalPersonal');
        hideModal('modalEditarPersonal');
        hideModal('modalDetallePersonal');
        hideModal('modalEliminarPersonal');
    }

    function requestJson(url, options = {}) {
        const headers = new Headers(options.headers || {});
        headers.set('X-Requested-With', 'XMLHttpRequest');

        return fetch(url, { credentials: 'same-origin', ...options, headers })
            .then(async (response) => {
                const rawText = await response.text();
                let data = null;

                try {
                    data = rawText ? JSON.parse(rawText) : {};
                } catch (error) {
                    const snippet = (rawText || '').replace(/\s+/g, ' ').slice(0, 140);
                    throw new Error(`Respuesta invalida del servidor (HTTP ${response.status}). ${snippet}`);
                }

                if (!response.ok) {
                    const msg = (data && (data.message || data.mensaje || data.detail)) || `HTTP ${response.status}`;
                    throw new Error(msg);
                }

                return data;
            });
    }

    function showLoadError(targetId, message) {
        const target = document.getElementById(targetId);
        if (!target) return;
        target.innerHTML = `
            <div class="personal-alert danger">
                <i class="fas fa-exclamation-triangle"></i>
                <span>${message}</span>
            </div>
        `;
    }

    function bindPersonalForm(formId, submitFn) {
        const form = document.getElementById(formId);
        if (!form || form.dataset.bound === '1') return;

        form.dataset.bound = '1';
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            submitFn(form);
        });
    }

    function enhanceCustomSelects() {
        const selects = document.querySelectorAll('#form-crear-personal select, #form-editar-personal select');

        selects.forEach((select) => {
            if (select.dataset.customized === '1') return;
            select.dataset.customized = '1';
            select.style.display = 'none';

            const wrapper = document.createElement('div');
            wrapper.className = 'custom-select-wrapper position-relative w-100';

            const trigger = document.createElement('div');
            trigger.className = 'personal-form-control d-flex align-items-center justify-content-between';
            trigger.style.cursor = 'pointer';
            trigger.style.backgroundColor = '#ffffff';
            trigger.style.paddingRight = '14px';
            trigger.style.height = '46px';
            trigger.style.color = '#111';

            const selectedOption = select.options[select.selectedIndex];
            const initialText = selectedOption ? selectedOption.text : 'Seleccione...';

            trigger.innerHTML = `
                <span class="custom-label" style="font-size: 0.95rem;">${initialText}</span>
                <i class="bi bi-chevron-down" style="color: #4b2f2a; font-size: 0.85rem;"></i>
            `;

            const menu = document.createElement('div');
            menu.className = 'custom-select-options position-absolute w-100 shadow-sm';
            menu.style.top = '100%';
            menu.style.left = '0';
            menu.style.marginTop = '6px';
            menu.style.backgroundColor = '#ffffff';
            menu.style.borderRadius = '16px';
            menu.style.border = '1px solid rgba(198, 162, 136, 0.2)';
            menu.style.zIndex = '1060';
            menu.style.display = 'none';
            menu.style.overflow = 'hidden';
            menu.style.padding = '6px 0';

            Array.from(select.options).forEach((opt) => {
                if (!opt.value && opt.text.trim().toLowerCase() === '---------') {
                    opt.text = 'Seleccione una opcion';
                }

                const val = opt.value;
                const text = opt.text;
                const item = document.createElement('div');
                item.className = 'custom-select-option px-3 py-2';
                item.style.cursor = 'pointer';
                item.style.transition = 'background-color 0.2s';
                item.style.fontSize = '0.95rem';
                item.style.color = '#4b2f2a';

                const isActive = select.value === val;
                item.style.fontWeight = isActive ? '700' : '500';
                item.style.backgroundColor = isActive ? '#eaddd3' : 'transparent';
                item.textContent = text;

                item.addEventListener('mouseenter', function () {
                    if (select.value !== val) {
                        this.style.backgroundColor = '#fbf5f0';
                    }
                });

                item.addEventListener('mouseleave', function () {
                    if (select.value !== val) {
                        this.style.backgroundColor = 'transparent';
                    }
                });

                item.addEventListener('click', function (e) {
                    e.stopPropagation();
                    select.value = val;
                    select.dispatchEvent(new Event('change', { bubbles: true }));
                    select.dispatchEvent(new Event('input', { bubbles: true }));
                    trigger.querySelector('.custom-label').innerText = text;

                    Array.from(menu.children).forEach((child) => {
                        child.style.backgroundColor = 'transparent';
                        child.style.fontWeight = '500';
                    });

                    this.style.backgroundColor = '#eaddd3';
                    this.style.fontWeight = '700';
                    menu.style.display = 'none';
                });

                menu.appendChild(item);
            });

            trigger.addEventListener('click', function (e) {
                e.stopPropagation();
                document.querySelectorAll('.custom-select-options').forEach((otherMenu) => {
                    if (otherMenu !== menu) otherMenu.style.display = 'none';
                });
                menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
            });

            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.attributeName !== 'class') return;

                    if (select.classList.contains('is-invalid')) {
                        trigger.style.borderColor = '#dc3545';
                        trigger.style.boxShadow = '0 0 0 0.25rem rgba(220, 53, 69, 0.25)';
                    } else if (select.classList.contains('is-valid')) {
                        trigger.style.borderColor = '#198754';
                        trigger.style.boxShadow = 'none';
                    } else {
                        trigger.style.borderColor = 'rgba(198, 162, 136, 0.5)';
                        trigger.style.boxShadow = 'none';
                    }
                });
            });

            observer.observe(select, { attributes: true });
            wrapper.appendChild(trigger);
            wrapper.appendChild(menu);
            select.parentNode.insertBefore(wrapper, select.nextSibling);
        });
    }

    function bindDynamicValidations() {
        if (typeof inicializarValidacionesPersonal === 'function') {
            inicializarValidacionesPersonal();
        }
        enhanceCustomSelects();
    }

    function enviarFormularioFiltro(form) {
        if (form) form.submit();
    }

    function personalSetFiltro(value, clickedEl) {
        const hiddenFiltro = document.getElementById('personal-hidden-filtro');
        const menu = document.getElementById('personal-filter-menu');
        if (!hiddenFiltro) return;

        hiddenFiltro.value = value;
        if (menu) menu.style.display = 'none';

        document.querySelectorAll('.personal-filter-option').forEach((el) => {
            el.classList.remove('active');
        });
        if (clickedEl) clickedEl.classList.add('active');

        const form = hiddenFiltro.form;
        if (!form) return;

        if (form._submitAjaxSearch) {
            form._submitAjaxSearch(true);
        } else {
            form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
        }
    }

    function personalClearFiltro() {
        const qInput = document.querySelector('#personal-filter-form [name=q]');
        if (qInput) qInput.value = '';
        personalSetFiltro('todos', document.querySelector('.personal-filter-option'));
    }

    function abrirModalPersonal() {
        showModal('modalPersonal');
        requestJson(urls.create)
            .then((data) => {
                const modalBody = document.getElementById('modalPersonalBody');
                if (!modalBody) return;
                modalBody.innerHTML = data.html_form;
                bindDynamicValidations();
                bindPersonalForm('form-crear-personal', enviarFormularioPersonal);
            })
            .catch((err) => {
                showLoadError('modalPersonalBody', err?.message || 'Error al cargar el formulario. Intenta nuevamente.');
            });
    }

    function cerrarModalPersonal() {
        hideModal('modalPersonal');
    }

    function enviarFormularioPersonal(form) {
        const formData = new FormData(form);
        requestJson(urls.create, { method: 'POST', body: formData })
            .then((data) => {
                if (data.success) {
                    cerrarModalPersonal();
                    Swal.fire({
                        title: 'Creado exitosamente',
                        text: data.message,
                        icon: 'success',
                        timer: 1500,
                        showConfirmButton: false,
                        confirmButtonColor: '#5d4037',
                    }).then(() => location.reload());
                    return;
                }

                const modalBody = document.getElementById('modalPersonalBody');
                if (!modalBody) return;
                modalBody.innerHTML = data.html_form;
                bindDynamicValidations();
                bindPersonalForm('form-crear-personal', enviarFormularioPersonal);
            })
            .catch((err) => {
                showLoadError('modalPersonalBody', err?.message || 'Error al guardar. Intenta nuevamente.');
            });
    }

    function abrirModalEditarPersonal(personalId) {
        showModal('modalEditarPersonal');
        requestJson(`/personal/${personalId}/editar/`)
            .then((data) => {
                const modalBody = document.getElementById('modalEditarPersonalBody');
                if (!modalBody) return;
                modalBody.innerHTML = data.html_form;
                bindDynamicValidations();
                bindPersonalForm('form-editar-personal', function (form) {
                    enviarFormularioEditarPersonal(form, personalId);
                });
            })
            .catch((err) => {
                showLoadError('modalEditarPersonalBody', err?.message || 'Error al cargar el formulario de edicion. Intenta nuevamente.');
            });
    }

    function cerrarModalEditarPersonal() {
        hideModal('modalEditarPersonal');
    }

    function enviarFormularioEditarPersonal(form, personalId) {
        const formData = new FormData(form);
        requestJson(`/personal/${personalId}/editar/`, { method: 'POST', body: formData })
            .then((data) => {
                if (data.success) {
                    cerrarModalEditarPersonal();
                    Swal.fire({
                        title: 'Actualizado exitosamente',
                        text: data.message,
                        icon: 'success',
                        timer: 1500,
                        showConfirmButton: false,
                        confirmButtonColor: '#5d4037',
                    }).then(() => location.reload());
                    return;
                }

                const modalBody = document.getElementById('modalEditarPersonalBody');
                if (!modalBody) return;
                modalBody.innerHTML = data.html_form;
                bindDynamicValidations();
                bindPersonalForm('form-editar-personal', function (newForm) {
                    enviarFormularioEditarPersonal(newForm, personalId);
                });
            })
            .catch((err) => {
                showLoadError('modalEditarPersonalBody', err?.message || 'Error al guardar cambios. Intenta nuevamente.');
            });
    }

    function abrirModalDetallePersonal(personalId) {
        showModal('modalDetallePersonal');
        requestJson(`/personal/${personalId}/detalle/`)
            .then((data) => {
                const modalBody = document.getElementById('modalDetallePersonalBody');
                if (!modalBody) return;
                modalBody.innerHTML = data.html_content;
            })
            .catch(() => {
                showLoadError('modalDetallePersonalBody', 'Error al cargar la informacion. Intenta nuevamente.');
            });
    }

    function cerrarModalDetallePersonal() {
        hideModal('modalDetallePersonal');
    }

    function performDeletePersonal(personalId) {
        const csrftoken = getCookie('csrftoken');
        return fetch(`/personal/${personalId}/eliminar/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken,
                'X-Requested-With': 'XMLHttpRequest',
            },
        })
            .then((response) => {
                if (!response.ok) throw new Error('Error en la solicitud');
                return response.json();
            })
            .then((data) => {
                if (!data.success) throw new Error(data.message || 'Error al eliminar');
                return data;
            });
    }

    function abrirModalEliminarPersonal(personalId) {
        Swal.fire({
            title: 'Estas seguro?',
            text: 'Esta accion no se puede deshacer',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#5d4037',
            cancelButtonColor: '#d33',
            confirmButtonText: 'Si, eliminar',
            cancelButtonText: 'Cancelar',
            showLoaderOnConfirm: true,
            preConfirm: () => performDeletePersonal(personalId).catch((error) => {
                Swal.showValidationMessage(`Error: ${error.message}`);
            }),
            allowOutsideClick: () => !Swal.isLoading(),
        }).then((result) => {
            if (!result.isConfirmed) return;
            Swal.fire({
                title: 'Eliminado',
                text: result.value.message || 'Personal eliminado exitosamente',
                icon: 'success',
                timer: 1500,
                showConfirmButton: false,
                confirmButtonColor: '#5d4037',
            }).then(() => location.reload());
        });
    }

    function confirmarEliminarPersonal(personalId) {
        performDeletePersonal(personalId)
            .then((data) => {
                hideModal('modalEliminarPersonal');
                Swal.fire({
                    title: 'Eliminado',
                    text: data.message || 'Personal eliminado exitosamente',
                    icon: 'success',
                    timer: 1500,
                    showConfirmButton: false,
                    confirmButtonColor: '#5d4037',
                }).then(() => location.reload());
            })
            .catch((error) => {
                Swal.fire({
                    title: 'Error',
                    text: error.message || 'No se pudo eliminar el personal.',
                    icon: 'error',
                    confirmButtonColor: '#5d4037',
                });
            });
    }

    function cerrarModalEliminarPersonal() {
        hideModal('modalEliminarPersonal');
    }

    function actualizarEstadoPersonal(switchElement) {
        const personalId = switchElement.dataset.personalId;
        const personalNombre = switchElement.dataset.personalNombre;
        const isChecked = switchElement.checked;
        const csrftoken = getCookie('csrftoken');

        switchElement.disabled = true;

        fetch(`/personal/${personalId}/toggle-activo/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken,
                'X-Requested-With': 'XMLHttpRequest',
            },
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.success) {
                    switchElement.disabled = false;
                    Swal.fire({
                        title: 'Estado actualizado',
                        text: `${personalNombre} ahora ${data.activo ? 'esta activo' : 'ya no esta activo'}`,
                        icon: 'success',
                        timer: 1800,
                        showConfirmButton: false,
                        confirmButtonColor: '#5d4037',
                    });
                    return;
                }

                switchElement.checked = !isChecked;
                switchElement.disabled = false;
                Swal.fire({
                    title: 'Error',
                    text: data.mensaje || 'Error al cambiar el estado',
                    icon: 'error',
                    confirmButtonColor: '#5d4037',
                });
            })
            .catch(() => {
                switchElement.checked = !isChecked;
                switchElement.disabled = false;
                Swal.fire({
                    title: 'Error de conexion',
                    text: 'No se pudo cambiar el estado. Intenta nuevamente.',
                    icon: 'error',
                    confirmButtonColor: '#5d4037',
                });
            });
    }

    function handleAction(actionEl) {
        const action = actionEl.dataset.personalAction;

        switch (action) {
            case 'open-create':
                abrirModalPersonal();
                break;
            case 'open-edit':
                abrirModalEditarPersonal(actionEl.dataset.personalId);
                break;
            case 'open-detail':
                abrirModalDetallePersonal(actionEl.dataset.personalId);
                break;
            case 'open-delete':
                abrirModalEliminarPersonal(actionEl.dataset.personalId);
                break;
            case 'confirm-delete':
                confirmarEliminarPersonal(actionEl.dataset.personalId);
                break;
            case 'close-modal':
                hideModal(actionEl.dataset.modalId);
                break;
            case 'toggle-filter-menu': {
                const menu = document.getElementById('personal-filter-menu');
                if (!menu) return;
                menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
                break;
            }
            case 'set-filter':
                personalSetFiltro(actionEl.dataset.filterValue || 'todos', actionEl);
                break;
            case 'clear-filter':
                personalClearFiltro();
                break;
            default:
                break;
        }
    }

    document.addEventListener('click', function (event) {
        const actionEl = event.target.closest('[data-personal-action]');
        if (actionEl) {
            event.preventDefault();
            handleAction(actionEl);
            return;
        }

        const filterWrap = document.querySelector('.personal-custom-filter-wrap');
        const menu = document.getElementById('personal-filter-menu');
        if (menu && filterWrap && !filterWrap.contains(event.target)) {
            menu.style.display = 'none';
        }

        if (!event.target.closest('.custom-select-wrapper')) {
            document.querySelectorAll('.custom-select-options').forEach((el) => {
                el.style.display = 'none';
            });
        }
    });

    document.addEventListener('change', function (e) {
        if (!e.target.classList.contains('toggle-activo-checkbox')) return;
        actualizarEstadoPersonal(e.target);
    });

    document.addEventListener('keydown', function (e) {
        if (e.key !== 'Escape') return;
        closeAllModals();
    });

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bindDynamicValidations);
    } else {
        bindDynamicValidations();
    }

    if (typeof window !== 'undefined') {
        window.abrirModalPersonal = abrirModalPersonal;
        window.cerrarModalPersonal = cerrarModalPersonal;
        window.abrirModalEditarPersonal = abrirModalEditarPersonal;
        window.cerrarModalEditarPersonal = cerrarModalEditarPersonal;
        window.abrirModalDetallePersonal = abrirModalDetallePersonal;
        window.cerrarModalDetallePersonal = cerrarModalDetallePersonal;
        window.abrirModalEliminarPersonal = abrirModalEliminarPersonal;
        window.confirmarEliminarPersonal = confirmarEliminarPersonal;
        window.cerrarModalEliminarPersonal = cerrarModalEliminarPersonal;
        window.personalSetFiltro = personalSetFiltro;
        window.personalClearFiltro = personalClearFiltro;
        window.bindDynamicValidationsPersonal = bindDynamicValidations;
        window.enviarFormularioFiltroPersonal = enviarFormularioFiltro;
    }
})();
