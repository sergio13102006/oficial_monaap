document.addEventListener('click', function (e) {
    const btn = e.target.closest('.btn-eliminar-cliente');
    if (!btn) return;

    const esAdmin = btn.dataset.esAdmin === 'true';
    const modalId = btn.dataset.modalId;

    if (!esAdmin) {
        const modalPermiso = document.getElementById('modalAccionNoPermitida');
        if (modalPermiso) {
            new bootstrap.Modal(modalPermiso).show();
        }
        return;
    }

    const modal = document.getElementById(modalId);
    if (modal) {
        new bootstrap.Modal(modal).show();
    }
});
