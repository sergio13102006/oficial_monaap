// static/proveedor/js/proveedor_formulario.js
(() => {
  "use strict";

  // =========================
  // Helpers DOM
  // =========================
  const qs = (root, sel) => (root || document).querySelector(sel);

  // =========================
  // CSRF
  // =========================
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(";").shift();
    return "";
  }

  function getCSRFToken() {
    return (
      document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
      getCookie("csrftoken") ||
      ""
    );
  }

  // =========================
  // fetchSmart
  // =========================
  async function fetchSmart(url, options = {}) {
    const res = await fetch(url, options);
    const contentType = (res.headers.get("content-type") || "").toLowerCase();

    if (contentType.includes("application/json")) {
      const data = await res.json();
      return { type: "json", ok: res.ok, status: res.status, data, res };
    }

    const text = await res.text();
    return { type: "html", ok: res.ok, status: res.status, data: text, res };
  }

  // =========================
  // ELIMINAR / DESACTIVAR
  // =========================
  async function eliminarProveedor(btn) {
    const id = btn.dataset.id;
    const nombre = btn.dataset.nombre || "este proveedor";
    const urlEliminar = btn.dataset.urlEliminar || `/Proveedores/eliminar/${id}/`;
    const urlDesactivar = btn.dataset.urlDesactivar || `/Proveedores/desactivar/${id}/`;

    const confirm = await Swal.fire({
      title: "Confirmar eliminación",
      text: `Esta acción intentará eliminar a ${nombre}.`,
      icon: "warning",
      showCancelButton: true,
      confirmButtonColor: "#d33",
      cancelButtonColor: "#6c757d",
      confirmButtonText: "Sí, eliminar",
      cancelButtonText: "Cancelar",
    });

    if (!confirm.isConfirmed) return;

    try {
      const csrf = getCSRFToken();

      const r = await fetch(urlEliminar, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": csrf,
          "X-Requested-With": "XMLHttpRequest",
        },
      });

      const ct = (r.headers.get("content-type") || "").toLowerCase();
      if (!ct.includes("application/json")) {
        throw new Error("Respuesta no JSON en eliminar");
      }

      const data = await r.json();

      // 1) Eliminado correctamente
      if (data.status === "deleted" || data.success === true && data.action === "deleted") {
        await Swal.fire({
          title: "Eliminado",
          text: data.message || "El proveedor fue eliminado correctamente.",
          icon: "success",
          confirmButtonColor: "#198754",
        });
        location.reload();
        return;
      }

      // 2) No se puede eliminar, pero sí desactivar
      const esProtegido =
        r.status === 409 ||
        data.status === "protected" ||
        data.action === "confirm_deactivate";

      if (esProtegido) {
        const cantidad = data.cantidad ?? 0;
        const detalle = data.detalle || "compras u otros registros";
        const mensaje =
          data.message ||
          `Este proveedor está relacionado con ${detalle}. No se puede eliminar, pero puedes desactivarlo.`;

        const ask = await Swal.fire({
          title: "No se puede eliminar",
          html: `
            ${mensaje}
            ${cantidad ? `<br><br>Registros relacionados: <strong>${cantidad}</strong>.` : ""}
            <br><br>¿Deseas desactivarlo en su lugar?
          `,
          icon: "info",
          showCancelButton: true,
          confirmButtonText: "Sí, desactivar",
          cancelButtonText: "Cancelar",
          confirmButtonColor: "#0d6efd",
          cancelButtonColor: "#6c757d",
        });

        if (!ask.isConfirmed) return;

        const r2 = await fetch(urlDesactivar, {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "X-CSRFToken": csrf,
            "X-Requested-With": "XMLHttpRequest",
          },
        });

        const ct2 = (r2.headers.get("content-type") || "").toLowerCase();
        if (!ct2.includes("application/json")) {
          throw new Error("Respuesta no JSON en desactivar");
        }

        const data2 = await r2.json();

        if (!r2.ok || !data2.success) {
          throw new Error(data2.message || "No se pudo desactivar el proveedor.");
        }

        await Swal.fire({
          title: "Proveedor desactivado",
          text: data2.message || "El proveedor fue desactivado correctamente.",
          icon: "success",
          confirmButtonColor: "#198754",
        });

        location.reload();
        return;
      }

      // 3) Otro error controlado del backend
      await Swal.fire({
        title: "Error",
        text: data.message || "No se pudo procesar la solicitud.",
        icon: "error",
        confirmButtonColor: "#d33",
      });
    } catch (err) {
      console.error("Error al eliminar/desactivar proveedor:", err);
      await Swal.fire({
        title: "Error",
        text: "Ocurrió un error al procesar la solicitud.",
        icon: "error",
        confirmButtonColor: "#d33",
      });
    }
  }

  // =========================
  // REACTIVAR
  // =========================
  async function reactivarProveedor(id) {
    const confirm = await Swal.fire({
      title: "Reactivar proveedor",
      text: "El proveedor volverá a estar disponible en el sistema.",
      icon: "question",
      showCancelButton: true,
      confirmButtonText: "Sí, reactivar",
      cancelButtonText: "Cancelar",
      confirmButtonColor: "#198754",
      cancelButtonColor: "#6c757d",
    });

    if (!confirm.isConfirmed) return;

    try {
      const csrf = getCSRFToken();

      const r = await fetch(`/Proveedores/reactivar/${id}/`, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": csrf,
          "X-Requested-With": "XMLHttpRequest",
        },
      });

      const ct = (r.headers.get("content-type") || "").toLowerCase();
      if (!ct.includes("application/json")) {
        throw new Error("Respuesta no JSON en reactivar");
      }

      const data = await r.json();

      if (!r.ok || !data.success) {
        throw new Error(data.message || "No fue posible reactivar el proveedor.");
      }

      await Swal.fire({
        title: "Proveedor reactivado",
        text: data.message || "El proveedor fue reactivado correctamente.",
        icon: "success",
        confirmButtonColor: "#198754",
      });

      location.reload();
    } catch (err) {
      console.error("Error al reactivar proveedor:", err);
      await Swal.fire({
        title: "Error",
        text: "No fue posible reactivar el proveedor.",
        icon: "error",
        confirmButtonColor: "#d33",
      });
    }
  }

  // =========================
  // MODAL AJAX genérico
  // =========================
  let modal = null;
  let modalEl = null;
  let modalTitleEl = null;
  let modalBodyEl = null;

  async function openModal(url, title) {
    if (!modal || !modalEl || !modalTitleEl || !modalBodyEl) return;

    modalTitleEl.textContent = title || "Formulario";
    modalBodyEl.innerHTML = `
      <div class="d-flex justify-content-center py-5">
        <div class="spinner-border" role="status" aria-hidden="true"></div>
      </div>
    `;
    modal.show();

    const result = await fetchSmart(url, {
      method: "GET",
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });

    if (result.type === "json") {
      modalTitleEl.textContent = result.data.title || title || "Formulario";
      modalBodyEl.innerHTML =
        result.data.html || `<div class="alert alert-danger">No se pudo cargar.</div>`;
    } else {
      modalBodyEl.innerHTML = result.data;
    }

    if (window.ProveedorFormulario) window.ProveedorFormulario.init(modalEl);
  }

  // =========================
  // VALIDACIONES PROVEEDOR
  // =========================
  function ensureWrapper(input) {
    if (!input) return null;

    const existing = input.closest(".form-validated");
    if (existing) return existing;

    const inputGroup = input.closest(".input-group");
    const target = inputGroup || input;

    const parent = target.parentElement;
    if (!parent) return null;

    const wrapper = document.createElement("div");
    wrapper.className = "form-validated";

    parent.insertBefore(wrapper, target);
    wrapper.appendChild(target);

    const icon = document.createElement("span");
    icon.className = "valid-check";
    icon.innerHTML = `<i class="bi bi-check-circle-fill text-success"></i>`;
    wrapper.appendChild(icon);

    return wrapper;
  }

  function getFeedbackEl(input) {
    if (!input) return null;

    const group = input.closest(".input-group");
    if (group) {
      let fb = group.parentElement?.querySelector(":scope > .invalid-feedback");
      if (!fb) {
        fb = document.createElement("div");
        fb.className = "invalid-feedback";
        group.insertAdjacentElement("afterend", fb);
      }
      return fb;
    }

    let fb = input.parentElement?.querySelector(":scope > .invalid-feedback");
    if (!fb) {
      fb = document.createElement("div");
      fb.className = "invalid-feedback";
      input.insertAdjacentElement("afterend", fb);
    }
    return fb;
  }

  function clearState(input) {
    if (!input) return;
    input.classList.remove("is-valid", "is-invalid");

    const wrapper = input.closest(".form-validated");
    if (wrapper) wrapper.classList.remove("is-ok");

    const fb = getFeedbackEl(input);
    if (fb) fb.textContent = "";
  }

  function markValid(input) {
    if (!input) return;

    const required = input.hasAttribute("required");
    const v = (input.value || "").trim();

    if (!required && !v) {
      clearState(input);
      return;
    }

    input.classList.remove("is-invalid");
    input.classList.add("is-valid");

    const fb = getFeedbackEl(input);
    if (fb) fb.textContent = "";

    const wrapper = ensureWrapper(input);
    if (wrapper) wrapper.classList.add("is-ok");
  }

  function markInvalid(input, msg) {
    if (!input) return;

    input.classList.remove("is-valid");
    input.classList.add("is-invalid");

    const wrapper = input.closest(".form-validated");
    if (wrapper) wrapper.classList.remove("is-ok");

    const fb = getFeedbackEl(input);
    if (fb) fb.textContent = msg || "Campo inválido";
  }

  const RE_NIT = /^[0-9]{5,20}$/;
  const RE_TEL = /^[0-9+\s()-]{7,20}$/;
  const RE_DIR = /^.{5,200}$/;

  function isEmailValid(input) {
    if (!input) return true;
    if (typeof input.checkValidity === "function") return input.checkValidity();
    const v = (input.value || "").trim();
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
  }

  function getSubmitButton(form) {
    return qs(form, "#btnGuardarProveedor") || qs(form, 'button[type="submit"]');
  }

  function validateProveedorForm(scope) {
    const form =
      scope?.tagName === "FORM" ? scope : qs(scope, "#proveedorForm") || qs(scope, "form");
    if (!form) return true;

    const errores = [];

    const nit = qs(form, "#id_nit");
    const nombre = qs(form, "#id_nombre_proveedor");
    const tel = qs(form, "#id_telefono_proveedor");
    const correo = qs(form, "#id_correo_proveedor");
    const dir = qs(form, "#id_direccion_proveedor");
    const estado = qs(form, "#id_estado");

    if (nit) {
      const v = (nit.value || "").trim();
      if (!v) { errores.push("nit"); markInvalid(nit, "NIT obligatorio"); }
      else if (!RE_NIT.test(v)) { errores.push("nit"); markInvalid(nit, "Solo números (5-20)"); }
      else markValid(nit);
    }

    if (nombre) {
      const v = (nombre.value || "").trim();
      if (!v) { errores.push("nombre"); markInvalid(nombre, "Nombre obligatorio"); }
      else if (v.length < 3) { errores.push("nombre"); markInvalid(nombre, "Mínimo 3 letras"); }
      else markValid(nombre);
    }

    if (tel) {
      const v = (tel.value || "").trim();
      if (!v) { errores.push("tel"); markInvalid(tel, "Teléfono obligatorio"); }
      else if (!RE_TEL.test(v)) { errores.push("tel"); markInvalid(tel, "Teléfono inválido"); }
      else markValid(tel);
    }

    if (correo) {
      const v = (correo.value || "").trim();
      if (!v) { errores.push("correo"); markInvalid(correo, "Correo obligatorio"); }
      else if (!isEmailValid(correo)) { errores.push("correo"); markInvalid(correo, "Correo inválido"); }
      else markValid(correo);
    }

    if (dir) {
      const v = (dir.value || "").trim();
      if (!v) { errores.push("dir"); markInvalid(dir, "Dirección obligatoria"); }
      else if (!RE_DIR.test(v)) { errores.push("dir"); markInvalid(dir, "Mínimo 5 caracteres"); }
      else markValid(dir);
    }

    if (estado) {
      const v = (estado.value || "").trim();
      if (!v) { errores.push("estado"); markInvalid(estado, "Obligatorio"); }
      else markValid(estado);
    }

    const btn = getSubmitButton(form);
    if (btn) btn.disabled = errores.length > 0;

    return errores.length === 0;
  }

  function wireProveedor(scope) {
    const root = scope || document;
    const form = qs(root, "#proveedorForm");
    if (!form) return;

    if (form.dataset.wiredProveedor === "1") return;
    form.dataset.wiredProveedor = "1";

    ["#id_nit", "#id_nombre_proveedor", "#id_telefono_proveedor", "#id_correo_proveedor", "#id_direccion_proveedor", "#id_estado"]
      .forEach((sel) => {
        const el = qs(form, sel);
        if (el) ensureWrapper(el);
      });

    form.addEventListener("input", (e) => {
      if (
        e.target.matches("#id_nit") ||
        e.target.matches("#id_nombre_proveedor") ||
        e.target.matches("#id_telefono_proveedor") ||
        e.target.matches("#id_correo_proveedor") ||
        e.target.matches("#id_direccion_proveedor")
      ) {
        validateProveedorForm(form);
      }
    });

    form.addEventListener("change", (e) => {
      if (e.target.matches("#id_estado")) validateProveedorForm(form);
    });

    validateProveedorForm(form);
  }

  window.ProveedorFormulario = {
    init(scope) { wireProveedor(scope || document); },
    validate(scope) { return validateProveedorForm(scope || document); },
  };

  // =========================
  // INIT + EVENTOS GLOBALES
  // =========================
  document.addEventListener("DOMContentLoaded", () => {
    modalEl = document.getElementById("ajaxFormModal");
    modalTitleEl = document.getElementById("ajaxFormModalTitle");
    modalBodyEl = document.getElementById("ajaxFormModalBody");

    if (modalEl && modalTitleEl && modalBodyEl) {
      modal = new bootstrap.Modal(modalEl);
    }

    document.addEventListener("click", async (e) => {
      const trigger = e.target.closest("[data-modal-url]");
      if (trigger) {
        e.preventDefault();
        await openModal(
          trigger.getAttribute("data-modal-url"),
          trigger.getAttribute("data-modal-title") || "Formulario"
        );
        return;
      }

      const btnDel = e.target.closest(".js-eliminar-proveedor");
      if (btnDel) {
        e.preventDefault();
        await eliminarProveedor(btnDel);
        return;
      }

      const btnRe = e.target.closest(".js-reactivar-proveedor");
      if (btnRe) {
        e.preventDefault();
        const id = btnRe.dataset.id;
        if (id) await reactivarProveedor(id);
        return;
      }
    });

    document.addEventListener("submit", async (e) => {
      const form = e.target.closest("#ajaxFormModal form");
      if (!form) return;

      e.preventDefault();

      if (form.id === "proveedorForm" && window.ProveedorFormulario) {
        const ok = window.ProveedorFormulario.validate(form);
        if (!ok) return;
      }

      const csrf =
        form.querySelector('input[name="csrfmiddlewaretoken"]')?.value ||
        getCSRFToken();

      const result = await fetchSmart(form.action, {
        method: "POST",
        body: new FormData(form),
        credentials: "same-origin",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": csrf,
        },
      });

      if (result.type === "json") {
        if (result.data?.success) {
          const esEdicion = Boolean(form.dataset.proveedorId);
          const successTitle = esEdicion ? "Proveedor actualizado" : "Proveedor guardado";
          const successText = result.data.message || (esEdicion
            ? "El proveedor se actualizó correctamente."
            : "El proveedor se guardó correctamente.");

          const finalizar = () => {
            modal?.hide();
            if (result.data.redirect_url) window.location.href = result.data.redirect_url;
            else window.location.reload();
          };

          if (typeof Swal !== "undefined" && Swal.fire) {
            await Swal.fire({
              title: successTitle,
              text: successText,
              icon: "success",
              confirmButtonText: "OK",
              confirmButtonColor: "#198754",
            });
          }

          finalizar();
          return;
        }

        modalTitleEl.textContent = result.data.title || modalTitleEl.textContent;
        modalBodyEl.innerHTML = result.data.html || `<div class="alert alert-danger mb-0">No se pudo guardar.</div>`;
        if (window.ProveedorFormulario) {
          window.ProveedorFormulario.init(modalBodyEl);
        }
        return;
      }

      modalBodyEl.innerHTML = result.data;
      if (window.ProveedorFormulario) window.ProveedorFormulario.init(modalEl);
    });

    wireProveedor(document);
  });

  document.addEventListener("shown.bs.modal", (e) => wireProveedor(e.target));
})();
