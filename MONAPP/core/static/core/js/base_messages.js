document.addEventListener('DOMContentLoaded', function () {
    const list = document.getElementById('base-messages');
    if (!list || typeof Swal === 'undefined') return;

    list.querySelectorAll('li').forEach(function (item) {
        const tags = (item.dataset.tags || '').toLowerCase();
        const text = item.textContent || '';

        const icon = tags.includes('success')
            ? 'success'
            : tags.includes('error')
                ? 'error'
                : tags.includes('warning')
                    ? 'warning'
                    : 'info';

        Swal.fire({
            icon: icon,
            title: 'Mensaje',
            text: text,
            confirmButtonText: 'OK',
        });
    });
});
