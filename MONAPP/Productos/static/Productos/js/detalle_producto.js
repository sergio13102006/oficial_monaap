document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("modalDetalleProducto");
  if (!modal) return;

  modal.addEventListener("show.bs.modal", (event) => {
    const btn = event.relatedTarget;
    if (!btn) return;

    const getText = (value, fallback = "—") =>
      value && String(value).trim() ? value : fallback;

    const nombre = getText(btn.dataset.nombre, "Producto");
    const codigo = getText(btn.dataset.codigo);
    const marca = getText(btn.dataset.marca);
    const precio = getText(btn.dataset.precio, "0");
    const linea = getText(btn.dataset.linea);
    const presentacion = getText(btn.dataset.presentacion);
    const unidad = getText(btn.dataset.unidad);
    const descripcion = getText(btn.dataset.descripcion, "Sin descripción");
    const imagen = (btn.dataset.imagen || "").trim();
    const activo = btn.dataset.activo === "1";

    const setText = (id, value) => {
      const el = document.getElementById(id);
      if (el) el.textContent = value;
    };

    setText("dp-nombre", nombre);
    setText("dp-codigo", codigo);
    setText("dp-marca", marca);
    setText("dp-precio", `$ ${precio}`);
    setText("dp-linea", linea);
    setText("dp-presentacion", presentacion);
    setText("dp-unidad", unidad);
    setText("dp-descripcion", descripcion);

    const avatar = document.getElementById("dp-avatar");
    if (avatar) {
      avatar.textContent = nombre.charAt(0).toUpperCase();
    }

    const estado = document.getElementById("dp-estado");
    if (estado) {
      estado.textContent = activo ? "Activo" : "Inactivo";
      estado.className = "detalle-pro-badge" + (activo ? "" : " is-inactive");
    }

    const img = document.getElementById("dp-imagen");
    const noimg = document.getElementById("dp-noimg");

    if (img && noimg) {
      if (imagen) {
        img.src = imagen;
        img.classList.remove("d-none");
        noimg.classList.add("d-none");
      } else {
        img.src = "";
        img.classList.add("d-none");
        noimg.classList.remove("d-none");
      }
    }
  });
});