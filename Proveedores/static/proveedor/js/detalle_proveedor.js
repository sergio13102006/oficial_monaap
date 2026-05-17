document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("modalDetalleProveedor");
  if (!modal) return;

  modal.addEventListener("show.bs.modal", (event) => {
    const button = event.relatedTarget;
    if (!button) return;

    const nombre = button.getAttribute("data-nombre") || "Proveedor";
    const nit = button.getAttribute("data-nit") || "—";
    const correo = button.getAttribute("data-correo") || "—";
    const estado = button.getAttribute("data-estado") || "—";
    const telefono = button.getAttribute("data-telefono") || "—";
    const direccion = button.getAttribute("data-direccion") || "—";

    const setText = (id, value) => {
      const el = document.getElementById(id);
      if (el) el.textContent = value;
    };

    setText("p-nombre", nombre);
    setText("p-nit", nit);
    setText("p-correo", correo);
    setText("p-estado", estado);
    setText("p-telefono", telefono);
    setText("p-direccion", direccion);

    const badge = document.getElementById("p-estado-badge");
    if (badge) {
      badge.textContent = estado;
      badge.classList.remove("activo", "inactivo", "is-active", "is-inactive");

      if (estado.toLowerCase().includes("activo")) {
        badge.classList.add("activo", "is-active");
      } else {
        badge.classList.add("inactivo", "is-inactive");
      }
    }

    const inicialesEl = document.getElementById("p-iniciales");
    if (inicialesEl) {
      const iniciales = nombre
        .trim()
        .split(/\s+/)
        .slice(0, 2)
        .map((p) => p.charAt(0).toUpperCase())
        .join("") || "PR";

      inicialesEl.textContent = iniciales;
    }
  });
});
