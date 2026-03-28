document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('formGestionDatos');
    const modal = document.getElementById('gestionDatosModal');

    if (!form || !modal || typeof bootstrap === 'undefined') return;

    const bsModal = new bootstrap.Modal(modal);

    form.addEventListener('submit', function (e) {
        e.preventDefault();

        const formData = new FormData(form);

        fetch(form.dataset.submitUrl || window.location.href, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Datos guardados correctamente');
                    bsModal.hide();
                    form.reset();
                    window.location.reload();
                } else {
                    alert('Error: ' + (data.message || 'No se pudieron guardar los datos'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Ocurrió un error al procesar la solicitud');
            });
    });

    modal.addEventListener('hidden.bs.modal', function () {
        form.reset();
    });
});
