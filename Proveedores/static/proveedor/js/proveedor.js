document.addEventListener("DOMContentLoaded", function () {
    const getCSRFToken = () => {
        const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : "";
    };

    const form = document.getElementById("busquedaProveedorForm");
    const wrapper = document.getElementById("busquedaProveedorForm");
    const box = document.getElementById("busquedaProveedorBox");
    const input = document.getElementById("busquedaProveedorInput");
    const btn = document.getElementById("btnBusquedaProveedorToggle");

    if (form && wrapper && box && input && btn) {
        function abrirBuscador() {
            wrapper.classList.add("is-open");
            box.classList.add("is-open");
            btn.setAttribute("aria-expanded", "true");

            setTimeout(() => {
                input.focus();
                const len = input.value.length;
                input.setSelectionRange(len, len);
            }, 180);
        }

        function cerrarBuscador() {
            wrapper.classList.remove("is-open");
            box.classList.remove("is-open");
            btn.setAttribute("aria-expanded", "false");
        }

        btn.addEventListener("click", function (e) {
            e.preventDefault();
            e.stopPropagation();

            const estaAbierto = wrapper.classList.contains("is-open");
            const texto = input.value.trim();

            if (!estaAbierto) {
                abrirBuscador();
                return;
            }

            if (texto) {
                form.submit();
                return;
            }

            cerrarBuscador();
        });

        input.addEventListener("keydown", function (e) {
            if (e.key === "Enter") {
                e.preventDefault();
                form.submit();
            }

            if (e.key === "Escape" && !input.value.trim()) {
                cerrarBuscador();
            }
        });

        document.addEventListener("click", function (e) {
            if (!wrapper.classList.contains("is-open")) return;
            if (wrapper.contains(e.target)) return;
            if (input.value.trim()) return;

            cerrarBuscador();
        });

        if (input.value.trim()) {
            abrirBuscador();
        }

        const rows = document.querySelectorAll("#proveedores-tbody tr");
        if (rows.length) {
            input.addEventListener("input", function () {
                const query = this.value.trim().toLowerCase();

                rows.forEach(row => {
                    const nombre = (row.getAttribute("data-nombre") || "").toLowerCase();
                    row.style.display = nombre.includes(query) ? "" : "none";
                });
            });
        }
    }

    document.querySelectorAll("a[data-confirm]").forEach(link => {
        link.addEventListener("click", function (e) {
            if (!confirm(this.getAttribute("data-confirm"))) {
                e.preventDefault();
            }
        });
    });

    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    if (typeof Inputmask !== "undefined") {
        Inputmask({ mask: "999.999.999-9", placeholder: " " }).mask("#id_nit");
        Inputmask({ mask: "(999) 999-9999", placeholder: " " }).mask("#id_telefono_proveedor");
    }

    const requiredFields = document.querySelectorAll(".form-proveedor [required]");
    requiredFields.forEach(field => {
        field.addEventListener("blur", function () {
            if (!this.value.trim()) {
                this.classList.add("is-invalid");
            } else {
                this.classList.remove("is-invalid");
            }
        });
    });

    const emailField = document.getElementById("id_correo_proveedor");
    if (emailField) {
        emailField.addEventListener("blur", function () {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (this.value.trim() && !emailRegex.test(this.value)) {
                this.classList.add("is-invalid");
            } else {
                this.classList.remove("is-invalid");
            }
        });
    }

    document.addEventListener("change", async function (e) {
        const input = e.target.closest(".js-toggle-proveedor-estado");
        if (!input || input.type !== "checkbox") return;

        const nombre = input.dataset.nombre || "el proveedor";
        const url = input.checked
            ? input.dataset.urlReactivar
            : input.dataset.urlDesactivar;

        if (!url) return;

        input.disabled = true;

        try {
            const response = await fetch(url, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "X-CSRFToken": getCSRFToken(),
                    "X-Requested-With": "XMLHttpRequest",
                },
            });

            const data = await response.json().catch(() => ({}));

            if (response.ok && data.success) {
                if (typeof Swal !== "undefined" && Swal.fire) {
                    await Swal.fire({
                        title: "Estado actualizado",
                        text: input.checked
                            ? `${nombre} ahora está activo`
                            : `${nombre} ahora ya no está activo`,
                        icon: "success",
                        confirmButtonText: "OK",
                        confirmButtonColor: "#4b2f2a",
                    });
                }
                window.location.reload();
                return;
            }

            input.checked = !input.checked;
            if (typeof Swal !== "undefined" && Swal.fire) {
                await Swal.fire({
                    title: "Error",
                    text: data.message || "No se pudo cambiar el estado del proveedor.",
                    icon: "error",
                    confirmButtonColor: "#d33",
                });
            } else {
                alert(data.message || "No se pudo cambiar el estado del proveedor.");
            }
        } catch (err) {
            console.error("Error cambiando estado del proveedor:", err);
            input.checked = !input.checked;
            if (typeof Swal !== "undefined" && Swal.fire) {
                await Swal.fire({
                    title: "Error",
                    text: "Ocurrió un error al cambiar el estado.",
                    icon: "error",
                    confirmButtonColor: "#d33",
                });
            } else {
                alert("Ocurrió un error al cambiar el estado.");
            }
        } finally {
            input.disabled = false;
        }
    });
});

