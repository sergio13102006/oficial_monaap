document.addEventListener('DOMContentLoaded', function() {
  const confirmModalEl = document.getElementById('confirmModal');
  if (!confirmModalEl) return;
  const confirmModal = new bootstrap.Modal(confirmModalEl);
  const modalBody = document.getElementById('confirmModalBody');
  const confirmBtn = document.getElementById('confirmModalConfirmBtn');
  let currentTarget = null;

  // Delegate clicks on elements with data-confirm
  document.body.addEventListener('click', function(e) {
    const el = e.target.closest('[data-confirm]');
    if (!el) return;
    e.preventDefault();

    const message = el.getAttribute('data-confirm') || '¿Estás seguro?';
    modalBody.textContent = message;
    currentTarget = el;

    confirmModal.show();
  });

  confirmBtn.addEventListener('click', function() {
    if (!currentTarget) {
      confirmModal.hide();
      return;
    }

    // Si está dentro de un formulario, lo enviamos
    const form = currentTarget.closest('form');
    if (form) {
      // si el botón estaba dentro del form, hacemos submit
      form.submit();
      confirmModal.hide();
      return;
    }

    // Si es un enlace, navegamos
    if (currentTarget.tagName === 'A') {
      window.location = currentTarget.getAttribute('href');
      confirmModal.hide();
      return;
    }

    // Caso por defecto: intentar desencadenar un click original
    try {
      currentTarget.click();
    } catch (err) {
      console.error('No se pudo ejecutar la acción tras confirmar', err);
    }

    confirmModal.hide();
  });
});