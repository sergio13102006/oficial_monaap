

/* ── Utilidad CSRF ── */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/* ════════════════════════════════
   MODAL: CREAR USUARIO
════════════════════════════════ */
function abrirModalUsuario() {
    const modal = document.getElementById('modalUsuario');
    const modalBody = document.getElementById('modalUsuarioBody');

    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';

    fetch(USUARIOS_URLS.crearUsuario, {
        method: 'GET',
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(response => response.json())
    .then(data => {
        modalBody.innerHTML = data.html_form;

        if (typeof inicializarValidacionesUsuario === 'function') {
            inicializarValidacionesUsuario();
        }

        const form = document.getElementById('form-crear-usuario');
        if (form) {
            form.addEventListener('submit', function (e) {
                e.preventDefault();
                enviarFormularioUsuario(form);
            });
        }
    })
    .catch(error => {
        console.error('Error:', error);
        modalBody.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle-fill me-2"></i>
                Error al cargar el formulario. Por favor, intenta nuevamente.
            </div>`;
    });
}

function cerrarModalUsuario() {
    document.getElementById('modalUsuario').style.display = 'none';
    document.body.style.overflow = '';
}

function enviarFormularioUsuario(form) {
    const formData = new FormData(form);
    const modalBody = document.getElementById('modalUsuarioBody');

    fetch(USUARIOS_URLS.crearUsuario, {
        method: 'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            cerrarModalUsuario();
            Swal.fire({
                title: '¡Creado exitosamente!',
                text: data.message,
                icon: 'success',
                confirmButtonColor: '#5d4037',
                background: '#fdfaf8',
                color: '#4b3621',
                timer: 1500,
                showConfirmButton: false
            }).then(() => location.reload());
        } else {
            modalBody.innerHTML = data.html_form;

            if (typeof inicializarValidacionesUsuario === 'function') {
                inicializarValidacionesUsuario();
            }

            const newForm = document.getElementById('form-crear-usuario');
            if (newForm) {
                newForm.addEventListener('submit', function (e) {
                    e.preventDefault();
                    enviarFormularioUsuario(newForm);
                });
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);
        modalBody.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle-fill me-2"></i>
                Error al guardar. Por favor, intenta nuevamente.
            </div>`;
    });
}

/* ════════════════════════════════
   MODAL: DESACTIVAR USUARIO
════════════════════════════════ */
function abrirModalEliminarUsuario(usuarioId) {
    Swal.fire({
        title: '¿Desactivar usuario?',
        text: 'El usuario quedará inactivo y podrás reactivarlo luego',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#5d4037',
        cancelButtonColor: '#d33',
        confirmButtonText: 'Sí, desactivar',
        cancelButtonText: 'Cancelar',
        background: '#fdfaf8',
        color: '#4b3621',
        showLoaderOnConfirm: true,
        preConfirm: () => {
            return desactivarUsuario(usuarioId).catch(error => {
                Swal.showValidationMessage(`Error: ${error.message}`);
            });
        },
        allowOutsideClick: () => !Swal.isLoading()
    }).then(result => {
        if (result.isConfirmed) {
            Swal.fire({
                title: '¡Desactivado!',
                text: result.value.message || 'Usuario desactivado exitosamente',
                icon: 'success',
                confirmButtonColor: '#5d4037',
                background: '#fdfaf8',
                color: '#4b3621',
                timer: 1500,
                showConfirmButton: false
            }).then(() => location.reload());
        }
    });
}

function desactivarUsuario(usuarioId) {
    const csrftoken = getCookie('csrftoken');

    return fetch(`/auth/usuarios/${usuarioId}/eliminar/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
            'X-Requested-With': 'XMLHttpRequest',
        },
    })
    .then(response => {
        if (!response.ok) throw new Error('Error en la solicitud');
        return response.json();
    })
    .then(data => {
        if (!data.success) throw new Error(data.message || 'Error al desactivar');
        return data;
    });
}

function confirmarEliminarUsuario(usuarioId) {
    desactivarUsuario(usuarioId)
        .then(data => {
            Swal.fire({
                title: '¡Desactivado!',
                text: data.message || 'Usuario desactivado exitosamente',
                icon: 'success',
                confirmButtonColor: '#5d4037',
                background: '#fdfaf8',
                color: '#4b3621',
                timer: 1500,
                showConfirmButton: false
            }).then(() => location.reload());
        })
        .catch(error => {
            Swal.fire({
                title: 'Error',
                text: error.message || 'No se pudo desactivar el usuario',
                icon: 'error',
                confirmButtonColor: '#5d4037',
                background: '#fdfaf8',
                color: '#4b3621'
            });
        });
}

/* ════════════════════════════════
   MODAL: DETALLE USUARIO
════════════════════════════════ */
function abrirModalDetalleUsuario(usuarioId) {
    const modal = document.getElementById('modalDetalleUsuario');
    const modalBody = document.getElementById('modalDetalleUsuarioBody');

    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';

    fetch(`/auth/usuarios/${usuarioId}/detalle/`, {
        method: 'GET',
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(response => response.json())
    .then(data => {
        modalBody.innerHTML = data.html_content;
    })
    .catch(error => {
        console.error('Error:', error);
        modalBody.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle-fill me-2"></i>
                Error al cargar la información. Intenta nuevamente.
            </div>`;
    });
}

function cerrarModalDetalleUsuario() {
    document.getElementById('modalDetalleUsuario').style.display = 'none';
    document.body.style.overflow = '';
}

/* ════════════════════════════════
   MODAL: EDITAR USUARIO
════════════════════════════════ */
function _configurarPreviewFoto(formSelector) {
    const fotoPerfil = document.querySelector(`${formSelector} input[name="foto_perfil"]`);
    if (!fotoPerfil) return;

    fotoPerfil.addEventListener('change', function (e) {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = function (e) {
            const preview = document.getElementById('preview-foto-editar');
            const container = document.getElementById('preview-foto-editar-container');
            const icon = container ? container.querySelector('i') : null;
            if (preview) { preview.src = e.target.result; preview.style.display = 'block'; }
            if (icon) { icon.style.display = 'none'; }
        };
        reader.readAsDataURL(file);
    });
}

function abrirModalEditarUsuario(usuarioId) {
    const modal = document.getElementById('modalEditarUsuario');
    const modalBody = document.getElementById('modalEditarUsuarioBody');

    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    modalBody.innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border text-secondary" role="status"></div>
            <p class="mt-2 mb-0">Cargando formulario...</p>
        </div>
    `;

    fetch(`/auth/usuarios/${usuarioId}/editar/`, {
        method: 'GET',
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(async response => {
        const contentType = response.headers.get('content-type') || '';

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Error ${response.status}: ${errorText.substring(0, 300)}`);
        }

        if (!contentType.includes('application/json')) {
            const text = await response.text();
            throw new Error(`La respuesta no es JSON válido: ${text.substring(0, 300)}`);
        }

        return response.json();
    })
    .then(data => {
        if (!data.success && !data.html_form) {
            throw new Error(data.message || 'No se pudo cargar el formulario.');
        }

        modalBody.innerHTML = data.html_form;

        const form = document.getElementById('form-editar-usuario');
        if (form) {
            form.addEventListener('submit', function (e) {
                e.preventDefault();
                enviarFormularioEditarUsuario(form, usuarioId);
            });
        }

        _configurarPreviewFoto('#form-editar-usuario');

        setTimeout(() => {
            if (typeof window.inicializarValidacionesEditarUsuario === 'function') {
                window.inicializarValidacionesEditarUsuario();
            }
        }, 200);
    })
    .catch(error => {
        console.error('Error al abrir modal editar:', error);

        modalBody.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle-fill me-2"></i>
                Error al cargar el formulario. Por favor, intenta nuevamente.
                <br><small>${error.message || 'Error desconocido del servidor'}</small>
            </div>
            <div class="text-end mt-3">
                <button type="button" class="btn btn-secondary" onclick="cerrarModalEditarUsuario()">
                    Cerrar
                </button>
            </div>
        `;
    });
}

function cerrarModalEditarUsuario() {
    const modal = document.getElementById('modalEditarUsuario');
    const modalBody = document.getElementById('modalEditarUsuarioBody');

    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('show');
    }

    if (modalBody) {
        modalBody.innerHTML = '';
    }

    document.body.style.overflow = '';
    document.body.classList.remove('modal-open');
}

function enviarFormularioEditarUsuario(form, usuarioId) {
    const formData = new FormData(form);
    const modalBody = document.getElementById('modalEditarUsuarioBody');

    fetch(`/auth/usuarios/${usuarioId}/editar/`, {
        method: 'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        body: formData
    })
    .then(async response => {
        const contentType = response.headers.get('content-type') || '';

        if (!contentType.includes('application/json')) {
            const text = await response.text();
            throw new Error(`Respuesta inválida del servidor: ${text.substring(0, 300)}`);
        }

        const data = await response.json();
        return { response, data };
    })
    .then(({ response, data }) => {
        if (data.success) {
            cerrarModalEditarUsuario();
            Swal.fire({
                title: '¡Actualizado exitosamente!',
                text: data.message,
                icon: 'success',
                confirmButtonColor: '#5d4037',
                background: '#fdfaf8',
                color: '#4b3621',
                timer: 1500,
                showConfirmButton: false
            }).then(() => location.reload());
            return;
        }

        if (data.html_form) {
            modalBody.innerHTML = data.html_form;

            const newForm = document.getElementById('form-editar-usuario');
            if (newForm) {
                newForm.addEventListener('submit', function (e) {
                    e.preventDefault();
                    enviarFormularioEditarUsuario(newForm, usuarioId);
                });
            }

            _configurarPreviewFoto('#form-editar-usuario');

            setTimeout(() => {
                if (typeof window.inicializarValidacionesEditarUsuario === 'function') {
                    window.inicializarValidacionesEditarUsuario();
                }
            }, 200);
            return;
        }

        throw new Error(data.message || `Error ${response.status} al guardar`);
    })
    .catch(error => {
        console.error('Error al guardar edición:', error);
        modalBody.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle-fill me-2"></i>
                Error al guardar. Por favor, intenta nuevamente.
                <br><small>${error.message}</small>
            </div>`;
    });
}
/* ════════════════════════════════
   EVENT DELEGATION & TECLADO
════════════════════════════════ */
document.addEventListener('click', function (e) {
    const actionBtn = e.target.closest('[data-usuario-action]');
    if (actionBtn) {
        const action = actionBtn.dataset.usuarioAction;
        if (action === 'open-create') abrirModalUsuario();
        if (action === 'close-create') cerrarModalUsuario();
        if (action === 'open-detail') abrirModalDetalleUsuario(actionBtn.dataset.usuarioId);
        if (action === 'close-detail') cerrarModalDetalleUsuario();
        if (action === 'open-edit') abrirModalEditarUsuario(actionBtn.dataset.usuarioId);
        if (action === 'close-edit') cerrarModalEditarUsuario();
        if (action === 'open-delete') abrirModalEliminarUsuario(actionBtn.dataset.usuarioId);
        if (action === 'confirm-delete') confirmarEliminarUsuario(actionBtn.dataset.usuarioId);
    }

    if (e.target.closest('.btn-detalle-usuario')) {
        const btn = e.target.closest('.btn-detalle-usuario');
        abrirModalDetalleUsuario(btn.getAttribute('data-usuario-id'));
    }
    if (e.target.closest('.btn-editar-usuario')) {
        const btn = e.target.closest('.btn-editar-usuario');
        abrirModalEditarUsuario(btn.getAttribute('data-usuario-id'));
    }
    if (e.target.closest('.btn-eliminar-usuario')) {
        const btn = e.target.closest('.btn-eliminar-usuario');
        abrirModalEliminarUsuario(btn.getAttribute('data-usuario-id'));
    }
});

document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
        cerrarModalUsuario();
        cerrarModalEditarUsuario();
        cerrarModalDetalleUsuario();
    }
});

/* ════════════════════════════════
   SWITCH ACTIVO / INACTIVO
════════════════════════════════ */
document.addEventListener('DOMContentLoaded', function () {
    const toggleCheckboxes = document.querySelectorAll('.toggle-activo-usuario-checkbox');

    toggleCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function () {
            const usuarioId = this.dataset.usuarioId;
            const usuarioNombre = this.dataset.usuarioNombre;
            const isChecked = this.checked;
            const switchEl = this;

            switchEl.disabled = true;

            fetch(`/auth/usuarios/${usuarioId}/toggle-activo/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest',
                },
            })
            .then(response => response.json())
            .then(data => {
                switchEl.disabled = false;
                if (data.success) {
                    Swal.fire({
                        title: '¡Estado actualizado!',
                        text: `${usuarioNombre} ahora ${data.activo ? 'está activo' : 'ya no está activo'}`,
                        icon: 'success',
                        confirmButtonColor: '#5d4037',
                        background: '#fdfaf8',
                        color: '#4b3621',
                        timer: 2000,
                        showConfirmButton: false
                    });
                } else {
                    switchEl.checked = !isChecked;
                    Swal.fire({
                        title: 'Error',
                        text: data.mensaje || 'Error al cambiar el estado',
                        icon: 'error',
                        confirmButtonColor: '#5d4037',
                        background: '#fdfaf8',
                        color: '#4b3621'
                    });
                }
            })
            .catch(error => {
                console.error('Error:', error);
                switchEl.checked = !isChecked;
                switchEl.disabled = false;
                Swal.fire({
                    title: 'Error de conexión',
                    text: 'No se pudo cambiar el estado. Intenta nuevamente.',
                    icon: 'error',
                    confirmButtonColor: '#5d4037',
                    background: '#fdfaf8',
                    color: '#4b3621'
                });
            });
        });
    });
});
function getUsuariosPageUrls() {
    const page = document.getElementById('usuarios-page');
    return {
        crearUsuario: page ? page.dataset.crearUsuarioUrl : '',
    };
}

const USUARIOS_URLS = getUsuariosPageUrls();
