(() => {
  document.addEventListener("DOMContentLoaded", () => {
    const getCookie = (name) => {
      const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
      return match ? decodeURIComponent(match[2]) : "";
    };

    const filtrosForm = document.getElementById("productosFiltrosForm");
    const lineaInput = document.getElementById("lineaFiltroProductos");

    if (filtrosForm && lineaInput) {
      filtrosForm.addEventListener("click", (e) => {
        const btn = e.target.closest("[data-linea]");
        if (!btn) return;

        lineaInput.value = btn.dataset.linea || "";
      });
    }

    document.addEventListener("change", async (e) => {
      const input = e.target.closest(".js-toggle-producto-estado");
      if (!input || input.type !== "checkbox") return;

      const url = input.dataset.url;
      if (!url) return;

      const nuevoEstado = input.checked;
      const nombre = input.dataset.nombre || "el producto";
      input.disabled = true;

      try {
        const response = await fetch(url, {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "X-CSRFToken": getCookie("csrftoken"),
            "X-Requested-With": "XMLHttpRequest",
          },
        });

        const data = await response.json().catch(() => ({}));

        if (response.ok && data.success) {
          input.dataset.activo = nuevoEstado ? "1" : "0";
          if (typeof Swal !== "undefined" && Swal.fire) {
            await Swal.fire({
              title: "Estado actualizado",
              text: nuevoEstado
                ? `${nombre} ahora está activo`
                : `${nombre} ahora ya no está activo`,
              icon: "success",
              confirmButtonColor: "#4b2f2a",
            });
          }
          window.location.reload();
          return;
        }

        input.checked = !nuevoEstado;
        alert(data.message || "No se pudo cambiar el estado del producto.");
      } catch (error) {
        console.error(error);
        input.checked = !nuevoEstado;
        alert("Error de conexión al cambiar el estado.");
      } finally {
        input.disabled = false;
      }
    });
  // =========================
// Buscador de productos
// =========================
const formBusqueda = document.getElementById("formBusquedaProductos");
const wrapperBusqueda = document.getElementById("busquedaProductosWrapper");
const boxBusqueda = document.getElementById("busquedaProductosBox");
const inputBusqueda = document.getElementById("busquedaProductosInput");
const btnBusquedaToggle = document.getElementById("btnBusquedaProductosToggle");

if (
  formBusqueda &&
  wrapperBusqueda &&
  boxBusqueda &&
  inputBusqueda &&
  btnBusquedaToggle
) {
  const abrirBuscador = () => {
    wrapperBusqueda.classList.add("is-open");
    boxBusqueda.classList.add("is-open");
    btnBusquedaToggle.setAttribute("aria-expanded", "true");

    setTimeout(() => {
      inputBusqueda.focus();
      const len = inputBusqueda.value.length;
      inputBusqueda.setSelectionRange(len, len);
    }, 180);
  };

  const cerrarBuscador = () => {
    wrapperBusqueda.classList.remove("is-open");
    boxBusqueda.classList.remove("is-open");
    btnBusquedaToggle.setAttribute("aria-expanded", "false");
  };

  const estaAbierto = () => boxBusqueda.classList.contains("is-open");

  btnBusquedaToggle.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();

    if (estaAbierto()) {
      cerrarBuscador();
      return;
    }

    abrirBuscador();
  });

  inputBusqueda.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      formBusqueda.requestSubmit();
    }

    if (e.key === "Escape") {
      e.preventDefault();

      if (inputBusqueda.value.trim()) {
        inputBusqueda.value = "";
      }

      cerrarBuscador();
    }
  });

  document.addEventListener("click", (e) => {
    if (!estaAbierto()) return;
    if (wrapperBusqueda.contains(e.target)) return;
    if (inputBusqueda.value.trim()) return;

    cerrarBuscador();
  });

  if (inputBusqueda.value.trim()) {
    abrirBuscador();
  }
}
    // =========================
    // 3) Modal detalle producto
    // =========================
    const modalDetalle = document.getElementById("modalDetalleProducto");

    if (modalDetalle) {
      modalDetalle.addEventListener("show.bs.modal", (event) => {
        const trigger = event.relatedTarget;
        if (!trigger) return;

        const d = trigger.dataset;

        const setText = (id, value) => {
          const el = document.getElementById(id);
          if (!el) return;

          const text = value && String(value).trim() ? value : "—";
          el.textContent = text;
        };

        setText("dp-codigo", d.codigo);
        setText("dp-nombre", d.nombre);
        setText("dp-marca", d.marca);
        setText("dp-precio", d.precio);
        setText("dp-linea", d.linea);
        setText("dp-unidad", d.unidad);
        setText("dp-presentacion", d.presentacion);

        const descEl = document.getElementById("dp-descripcion");
        if (descEl) {
          descEl.textContent =
            d.descripcion && d.descripcion.trim()
              ? d.descripcion
              : "Sin descripción.";
        }

        const estadoEl = document.getElementById("dp-estado");
        if (estadoEl) {
          const activo = d.activo === "1";
          estadoEl.textContent = activo ? "Activo" : "Inactivo";
          estadoEl.classList.toggle("is-inactive", !activo);
        }

        const avatarEl = document.getElementById("dp-avatar");
        if (avatarEl) {
          const inicial = d.nombre && d.nombre.trim()
            ? d.nombre.trim().charAt(0).toUpperCase()
            : "P";
          avatarEl.textContent = inicial;
        }

        const imgEl = document.getElementById("dp-imagen");
        const noImgEl = document.getElementById("dp-noimg");

        if (imgEl) {
          if (d.imagen && d.imagen.trim()) {
            imgEl.src = d.imagen;
            imgEl.classList.remove("d-none");
            imgEl.classList.remove("js-img-zoom");
            imgEl.removeAttribute("data-src");

            if (noImgEl) {
              noImgEl.classList.add("d-none");
            }
          } else {
            imgEl.src = "";
            imgEl.classList.add("d-none");
            imgEl.removeAttribute("data-src");

            if (noImgEl) {
              noImgEl.classList.remove("d-none");
            }
          }
        }
      });
    }

    // =========================
    // 4) Zoom imagen
    // =========================
    document.addEventListener("click", (e) => {
      const img = e.target.closest(".js-img-zoom");
      if (!img) return;

      e.preventDefault();

      const src = img.getAttribute("data-src") || img.getAttribute("src");
      const modalImagen = document.getElementById("modalImagen");
      const modalImagenTag = document.getElementById("modalImagenTag");

      if (!src || !modalImagen || !modalImagenTag) return;

      modalImagenTag.src = src;
      new bootstrap.Modal(modalImagen).show();
    });

    const modalImagen = document.getElementById("modalImagen");
    if (modalImagen) {
      modalImagen.addEventListener("hidden.bs.modal", () => {
        const modalImagenTag = document.getElementById("modalImagenTag");
        if (modalImagenTag) {
          modalImagenTag.src = "";
        }
      });
    }
  });
})();



