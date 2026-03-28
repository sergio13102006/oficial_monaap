function getGestionCookie(name) {
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

function execScriptsInContainer(container) {
    container.querySelectorAll('script').forEach((old) => {
        const script = document.createElement('script');
        if (old.src) {
            script.src = old.src;
        } else {
            script.textContent = old.textContent;
        }
        old.parentNode.replaceChild(script, old);
    });
}

document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('modalFormGestion');
    const modalContent = document.getElementById('modalFormContent');
    const modalInfo = document.getElementById('modalGestionInfo');
    const modalInfoTitle = document.getElementById('modalGestionInfoLabel');
    const modalInfoContent = document.getElementById('modalGestionInfoContent');
    const modalFormTitle = document.getElementById('modalFormGestionLabel');
    const btnReporte = document.getElementById('btnReportePdfPreview');

    const spinnerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Cargando...</span>
            </div>
            <p class="mt-3">Cargando formulario...</p>
        </div>`;

    function cargarFormularioGestion(url) {
        if (!modalContent) return;
        modalContent.innerHTML = spinnerHTML;

        fetch(url)
            .then((r) => r.text())
            .then((html) => {
                modalContent.innerHTML = html;
                execScriptsInContainer(modalContent);
                if (window.initGestionForm) {
                    window.initGestionForm(modalContent);
                }
            })
            .catch(() => {
                modalContent.innerHTML = `
                    <div class="alert alert-danger m-3">
                        <i class="bi bi-exclamation-triangle"></i>
                        Error al cargar el formulario. Por favor, intenta nuevamente.
                    </div>`;
            });
    }

    document.addEventListener('click', function (event) {
        const triggerForm = event.target.closest('.js-open-gestion-form-modal');
        if (triggerForm && modal) {
            event.preventDefault();
            event.stopImmediatePropagation();
            const url = triggerForm.dataset.formUrl || '';
            modal.dataset.loadUrl = url;
            modal.dataset.manualLoaded = '1';
            if (modalFormTitle) {
                modalFormTitle.innerHTML = `<i class="bi bi-file-earmark-plus"></i> ${triggerForm.dataset.formTitle || 'Gestion de datos'}`;
            }
            cargarFormularioGestion(url);
            bootstrap.Modal.getOrCreateInstance(modal).show();
            return;
        }

        const triggerInfo = event.target.closest('.js-open-gestion-info-modal');
        if (triggerInfo && modalInfo && modalInfoContent) {
            event.preventDefault();
            const url = triggerInfo.getAttribute('href');
            if (!url) return;

            if (modalInfoTitle) {
                modalInfoTitle.textContent = triggerInfo.dataset.modalTitle || 'Detalle';
            }
            modalInfoContent.innerHTML = spinnerHTML;
            bootstrap.Modal.getOrCreateInstance(modalInfo).show();

            fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then((r) => r.text())
                .then((html) => {
                    modalInfoContent.innerHTML = html;
                    execScriptsInContainer(modalInfoContent);
                    if (window.initGestionForm) {
                        window.initGestionForm(modalInfoContent);
                    }
                })
                .catch(() => {
                    modalInfoContent.innerHTML = `
                        <div class="alert alert-danger mb-0">
                            Error al cargar la informacion.
                        </div>`;
                });
        }
    });

    if (modal) {
        modal.addEventListener('show.bs.modal', function () {
            if (modal.dataset.manualLoaded === '1') {
                modal.dataset.manualLoaded = '0';
                return;
            }
            const url = modal.dataset.loadUrl || '';
            if (url) {
                cargarFormularioGestion(url);
            }
        });

        modal.addEventListener('hidden.bs.modal', function () {
            modal.dataset.loadUrl = '';
            modal.dataset.manualLoaded = '0';
        });
    }

    async function eliminarGestionConSweetAlert(deleteUrl, label) {
        if (!deleteUrl) return;

        if (typeof Swal === 'undefined') {
            if (!confirm('Eliminar este registro?')) return;
        } else {
            const result = await Swal.fire({
                title: 'Eliminar registro?',
                text: label ? `Se eliminara: ${label}` : 'Esta accion no se puede deshacer.',
                icon: 'warning',
                showCancelButton: true,
                confirmButtonText: 'Si, eliminar',
                cancelButtonText: 'Cancelar',
                reverseButtons: true,
                buttonsStyling: false,
                customClass: {
                    confirmButton: 'btn btn-danger me-2',
                    cancelButton: 'btn btn-secondary',
                },
            });
            if (!result.isConfirmed) return;
        }

        try {
            const response = await fetch(deleteUrl, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getGestionCookie('csrftoken'),
                },
            });
            const data = await response.json();

            if (data && data.success) {
                if (modalInfo) {
                    bootstrap.Modal.getOrCreateInstance(modalInfo).hide();
                }
                if (typeof Swal !== 'undefined') {
                    await Swal.fire({
                        icon: 'success',
                        title: 'Eliminado',
                        text: data.message || 'Registro eliminado correctamente.',
                        timer: 1300,
                        showConfirmButton: false,
                    });
                }
                window.location.reload();
                return;
            }

            if (typeof Swal !== 'undefined') {
                Swal.fire('Error', (data && data.message) || 'No se pudo eliminar.', 'error');
            } else {
                alert((data && data.message) || 'No se pudo eliminar.');
            }
        } catch (error) {
            if (typeof Swal !== 'undefined') {
                Swal.fire('Error', 'No se pudo eliminar el registro.', 'error');
            } else {
                alert('No se pudo eliminar el registro.');
            }
        }
    }

    document.addEventListener('click', function (event) {
        const deleteTrigger = event.target.closest('.js-delete-gestion-swal');
        if (!deleteTrigger) return;
        event.preventDefault();
        eliminarGestionConSweetAlert(deleteTrigger.dataset.deleteUrl, deleteTrigger.dataset.gestionLabel || '');
    });

    if (btnReporte) {
        btnReporte.addEventListener('click', function () {
            const form = document.getElementById('filtrosForm');
            const params = new URLSearchParams();

            if (form) {
                const buscarInput = form.querySelector('input[name="buscar"]');
                const formaInput = form.querySelector('select[name="forma_natural"]');
                const porosidadInput = form.querySelector('select[name="porosidad"]');
                const texturaInput = form.querySelector('select[name="textura"]');
                const estadoInput = form.querySelector('select[name="estado_pago"]');

                params.set('buscar', buscarInput ? buscarInput.value : '');
                params.set('forma_natural', formaInput ? formaInput.value : '');
                params.set('porosidad', porosidadInput ? porosidadInput.value : '');
                params.set('textura', texturaInput ? texturaInput.value : '');
                params.set('estado_pago', estadoInput ? estadoInput.value : '');
            }

            const baseUrl = btnReporte.dataset.previewBase || '';
            btnReporte.dataset.previewUrl = baseUrl + '?' + params.toString();
        }, true);
    }
});

window.initGestionForm = initGestionForm;
