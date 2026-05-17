document.addEventListener('DOMContentLoaded', () => {

    const numericInputs = document.querySelectorAll('input[data-only="number"]');

    numericInputs.forEach(input => {

        // Bloquea cualquier tecla que no sea número
        input.addEventListener('keydown', (e) => {
            const allowedKeys = [
                'Backspace', 'Delete', 'ArrowLeft', 'ArrowRight',
                'Tab', 'Home', 'End'
            ];

            if (
                allowedKeys.includes(e.key) ||
                (e.key >= '0' && e.key <= '9')
            ) {
                return;
            }

            e.preventDefault();
        });

        // Limpia cualquier carácter no numérico (por si acaso)
        input.addEventListener('input', () => {
            input.value = input.value.replace(/[^0-9]/g, '');
        });

        // Bloquea pegar texto con letras
        input.addEventListener('paste', (e) => {
            const text = (e.clipboardData || window.clipboardData).getData('text');
            if (!/^\d+$/.test(text)) {
                e.preventDefault();
            }
        });

    });

});
document.addEventListener('DOMContentLoaded', () => {

    // SOLO NÚMEROS
    const soloNumeros = document.querySelectorAll(
        'input[name="nit"], input[name="telefono_proveedor"], input[name="id_venta"], input[name="codigo_marca"]'
    );

    soloNumeros.forEach(input => {
        input.addEventListener('input', () => {
            input.value = input.value.replace(/\D/g, '');
        });
    });

    // SOLO LETRAS
    const soloLetras = document.querySelectorAll(
        'input[name="nombre_proveedor"], input[name="nombre_encargado"]'
    );

    soloLetras.forEach(input => {
        input.addEventListener('input', () => {
            input.value = input.value.replace(/[^A-Za-zÁÉÍÓÚáéíóúÑñ ]/g, '');
        });
    });

});
const ccEncargado = document.querySelector('input[name="cc_encargado"]');

if (ccEncargado) {
    ccEncargado.addEventListener('input', () => {
        ccEncargado.value = ccEncargado.value.replace(/\D/g, '');
    });
}
