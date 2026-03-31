(() => {
  "use strict";

  const MAX_CANTIDAD_COMPRA = 1000000;

  const qs = (root, sel) => (root || document).querySelector(sel);
  const qsa = (root, sel) => Array.from((root || document).querySelectorAll(sel));

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(";").shift();
    return "";
  }

  function csrfFromCookie() {
    return getCookie("csrftoken") || "";
  }

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

  function toNumber(value) {
    if (value === null || value === undefined || value === "") return 0;
    const raw = String(value).trim();
    const normalized = raw.replace(/\./g, "").replace(",", ".");
    const parsed = Number(normalized);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function formatCOPNumber(value) {
    const n = Math.round(Number(value) || 0);
    return n.toLocaleString("es-CO");
  }

  function unformatCOP(value) {
    return String(value || "").replace(/\D/g, "");
  }

  function formatCOPDigitsOnly(value) {
    const digits = String(value || "").replace(/\D/g, "");
    const n = parseInt(digits || "0", 10);
    return n.toLocaleString("es-CO");
  }

  function renderCompraAnulada(row) {
    if (!row) return;

    const estadoCell = row.querySelector("td:nth-child(5)");
    const accionesCell = row.querySelector("td:nth-child(6)");

    if (estadoCell) {
      estadoCell.innerHTML = `
        <span class="compras-state-pill is-off" aria-label="Compra anulada" title="Anulada">
          <span class="compras-state-pill__knob"></span>
        </span>
      `;
    }

    if (accionesCell) {
      accionesCell.innerHTML = `
        <span class="badge bg-secondary">Sin acciones</span>
      `;
    }
  }

  const INPUT_RULES = {
    numeric: {
      pattern: /[^\d]/g,
      allow: (text) => /^\d*$/.test(text),
    },
    money: {
      pattern: /[^\d.,\s]/g,
      allow: (text) => /^[\d.,\s]*$/.test(text),
    },
    text: {
      pattern: /[^\p{L}\p{N}\s]/gu,
      allow: (text) => /^[\p{L}\p{N}\s]*$/u.test(text),
    },
  };

  function bindRestrictedInput(input, ruleName) {
    if (!input || input.dataset.guardWired === "1" || !INPUT_RULES[ruleName]) return;
    input.dataset.guardWired = "1";

    const rule = INPUT_RULES[ruleName];
    const sanitize = () => {
      const cleaned = String(input.value || "").replace(rule.pattern, "");
      if (cleaned !== input.value) {
        input.value = cleaned;
      }
    };

    input.addEventListener("beforeinput", (e) => {
      if (!e.inputType || !e.inputType.startsWith("insert")) return;
      if (!rule.allow(e.data || "")) e.preventDefault();
    });

    input.addEventListener("paste", (e) => {
      const pasted = e.clipboardData?.getData("text") || "";
      if (!rule.allow(pasted)) {
        e.preventDefault();
        sanitize();
      }
    });

    input.addEventListener("input", sanitize);
  }

  function wireCompraGuards(scope = document) {
    const root = scope || document;

    qsa(root, 'input[name$="-cantidad"]').forEach((input) => bindRestrictedInput(input, "numeric"));
    qsa(root, 'input[name$="-precio_unitario"]').forEach((input) => bindRestrictedInput(input, "money"));
    qsa(root, "#id_observacion").forEach((input) => bindRestrictedInput(input, "text"));
  }

  function attachCOPMask(input) {
    if (!input || input.dataset.copMaskBound === "1") return;
    input.dataset.copMaskBound = "1";

    input.addEventListener("input", () => {
      input.value = formatCOPDigitsOnly(input.value);
      input.setSelectionRange(input.value.length, input.value.length);
    });

    if (input.value) {
      input.value = formatCOPDigitsOnly(input.value);
    }
  }

  function hideGeneralErrors(form) {
    const box = qs(form, "#compraErroresGenerales");
    if (!box) return;
    box.classList.add("d-none");
    box.innerHTML = "";
  }

  function showGeneralErrors(form, errores) {
    const box = qs(form, "#compraErroresGenerales");
    if (!box || !errores || !errores.length) return;

    box.innerHTML = errores.map((e) => `<div>${e}</div>`).join("");
    box.classList.remove("d-none");
  }

  function ensureFeedback(input) {
    if (!input) return null;

    const inputGroup = input.closest(".input-group");
    const anchor = inputGroup || input;

    let feedback = anchor.parentElement?.querySelector(".invalid-feedback");
    if (!feedback) {
      feedback = document.createElement("div");
      feedback.className = "invalid-feedback";
      anchor.insertAdjacentElement("afterend", feedback);
    }

    return feedback;
  }

  function markInvalid(input, message) {
    if (!input) return;
    input.classList.add("is-invalid");
    input.classList.remove("is-valid");
    const feedback = ensureFeedback(input);
    if (feedback) feedback.textContent = message || "Campo inválido.";
  }

  function markValid(input) {
    if (!input) return;
    input.classList.remove("is-invalid");
    input.classList.add("is-valid");
    const feedback = ensureFeedback(input);
    if (feedback) feedback.textContent = "";
  }

  function clearState(input) {
    if (!input) return;
    input.classList.remove("is-invalid", "is-valid");
    const feedback = ensureFeedback(input);
    if (feedback) feedback.textContent = "";
  }

  function calcularTotal(scope) {
    const root = scope || document;
    const totalInput = qs(root, "#id_precio_total");
    if (!totalInput) return;

    let total = 0;

    qsa(root, ".detalle-item").forEach((item) => {
      if (item.classList.contains("d-none")) return;

      const deleteInput = qs(item, 'input[name$="-DELETE"]');
      if (deleteInput && deleteInput.checked) return;

      const cantidadInput = qs(item, 'input[name$="-cantidad"]');
      const precioInput = qs(item, 'input[name$="-precio_unitario"]');

      if (!cantidadInput || !precioInput) return;

      const cantidad = toNumber(cantidadInput.value);
      const precio = toNumber(precioInput.value);

      if (cantidad > 0 && precio > 0) {
        total += cantidad * precio;
      }
    });

    totalInput.value = formatCOPNumber(total);
  }

  function renumerarForms(container, prefix) {
    const items = Array.from(container.querySelectorAll(".detalle-item"));

    items.forEach((item, newIndex) => {
      item.querySelectorAll("input, select, textarea, label").forEach((el) => {
        if (el.name) {
          el.name = el.name.replace(
            new RegExp(`^${prefix}-(\\d+)-`),
            `${prefix}-${newIndex}-`
          );
        }

        if (el.id) {
          el.id = el.id.replace(
            new RegExp(`^id_${prefix}-(\\d+)-`),
            `id_${prefix}-${newIndex}-`
          );
        }

        const htmlFor = el.getAttribute?.("for");
        if (htmlFor) {
          el.setAttribute(
            "for",
            htmlFor.replace(
              new RegExp(`^id_${prefix}-(\\d+)-`),
              `id_${prefix}-${newIndex}-`
            )
          );
        }
      });
    });
  }

  function getFormActivos(form) {
    return qsa(form, ".detalle-item").filter((item) => {
      if (item.classList.contains("d-none")) return false;
      const deleteInput = qs(item, 'input[name$="-DELETE"]');
      return !(deleteInput && deleteInput.checked);
    });
  }

  function validateCompraForm(scope, options = {}) {
    const { showErrors = true } = options;
    const root = scope || document;
    const form =
      root?.tagName === "FORM"
        ? root
        : qs(root, "#formCompra") || qs(document, "#formCompra");

    if (!form) return true;

    hideGeneralErrors(form);

    const errores = [];
    const btnGuardar = qs(form, "#btnGuardarCompra");
    const modo = (form.dataset.modo || "crear").trim();
    const itemsActivos = getFormActivos(form);
    const pintarErrores = showErrors === true;

    const proveedor = qs(form, "#id_proveedor");
    if (proveedor) {
      if (!String(proveedor.value || "").trim()) {
        errores.push("Selecciona un proveedor.");
        if (pintarErrores) markInvalid(proveedor, "Proveedor obligatorio.");
      } else {
        if (pintarErrores) markValid(proveedor);
      }
    }

    const productosUsados = new Map();
    let hayProductoReal = false;

    itemsActivos.forEach((item, idx) => {
      const productoSel = qs(item, 'select[name$="-producto"]');
      const cantidadInp = qs(item, 'input[name$="-cantidad"]');
      const precioInp = qs(item, 'input[name$="-precio_unitario"]');

      const productoVal = String(productoSel?.value || "").trim();
      const cantidadRaw = String(cantidadInp?.value || "").trim();
      const precioRaw = String(precioInp?.value || "").trim();

      const filaVacia = !productoVal && !cantidadRaw && !precioRaw;

      if (filaVacia) {
        clearState(productoSel);
        clearState(cantidadInp);
        clearState(precioInp);
        return;
      }

      if (!productoVal) {
        errores.push(`Debes seleccionar un producto en la fila ${idx + 1}.`);
        if (pintarErrores) markInvalid(productoSel, "Selecciona un producto.");
      } else {
        hayProductoReal = true;
        if (pintarErrores) markValid(productoSel);
        productosUsados.set(productoVal, (productosUsados.get(productoVal) || 0) + 1);
      }

      const cantidad = toNumber(cantidadRaw);
      if (!Number.isInteger(cantidad) || cantidad <= 0) {
        errores.push(`La cantidad de la fila ${idx + 1} debe ser un entero mayor que 0.`);
        if (pintarErrores) markInvalid(cantidadInp, "Cantidad inválida.");
      } else if (cantidad > MAX_CANTIDAD_COMPRA) {
        errores.push(`La cantidad de la fila ${idx + 1} supera el máximo permitido.`);
        if (pintarErrores) markInvalid(cantidadInp, `Máximo ${MAX_CANTIDAD_COMPRA}.`);
      } else {
        if (pintarErrores) markValid(cantidadInp);
      }

      const precio = toNumber(precioRaw);
      if (precio <= 0) {
        errores.push(`El precio unitario de la fila ${idx + 1} debe ser mayor que 0.`);
        if (pintarErrores) markInvalid(precioInp, "Precio inválido.");
      } else {
        if (pintarErrores) markValid(precioInp);
      }
    });

    if (!hayProductoReal) {
      errores.push("Debes agregar al menos un producto a la compra.");
    }

    for (const [productoId, count] of productosUsados.entries()) {
      if (count > 1) {
        errores.push("No puedes repetir el mismo producto en la compra.");
        if (pintarErrores) {
          qsa(form, 'select[name$="-producto"]').forEach((sel) => {
            if (String(sel.value || "") === String(productoId)) {
              markInvalid(sel, "Producto duplicado.");
            }
          });
        }
        break;
      }
    }

    if (modo === "editar" && itemsActivos.length === 0) {
      errores.push("No puedes dejar la compra sin productos.");
    }

    if (errores.length && showErrors) {
      showGeneralErrors(form, [...new Set(errores)]);
    }

    const ok = errores.length === 0;
    if (btnGuardar) btnGuardar.disabled = !ok;
    return ok;
  }

  let formModal = null;
  const formModalEl = document.getElementById("ajaxFormModal");
  const formModalTitleEl = document.getElementById("ajaxFormModalTitle");
  const formModalBodyEl = document.getElementById("ajaxFormModalBody");

  if (formModalEl) {
    formModal = new bootstrap.Modal(formModalEl);
  }

  let detalleModal = null;
  const detalleModalEl = document.getElementById("modalDetalleCompra");
  const detalleBodyEl = document.getElementById("detalleCompraBody");
  const detalleTitleEl = document.getElementById("modalDetalleCompraTitle");

  if (detalleModalEl) {
    detalleModal = new bootstrap.Modal(detalleModalEl);
  }

  function initCompraForm(scope) {
    wireCompraGuards(scope || document);
    qsa(scope || document, 'input[name$="-precio_unitario"]').forEach(attachCOPMask);
    calcularTotal(scope || document);
    validateCompraForm(scope || document, { showErrors: false });
  }

  async function openFormModal(url, title) {
    if (!formModal || !formModalTitleEl || !formModalBodyEl) return;

    formModalTitleEl.textContent = title || "Formulario";
    formModalBodyEl.innerHTML = `
      <div class="d-flex justify-content-center py-5">
        <div class="spinner-border" role="status" aria-hidden="true"></div>
      </div>
    `;
    formModal.show();

    const result = await fetchSmart(url, {
      method: "GET",
      credentials: "same-origin",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
      },
    });

    formModalBodyEl.innerHTML =
      result.type === "json"
        ? result.data.html || `<div class="alert alert-danger">No se pudo cargar.</div>`
        : result.data;

    initCompraForm(formModalEl);
    setTimeout(() => {
      window.initDevolucionForm?.(formModalEl);
    }, 0);
  }

  document.body.addEventListener("click", async (e) => {
    const trigger = e.target.closest("[data-modal-url]");
    if (trigger) {
      e.preventDefault();
      await openFormModal(
        trigger.getAttribute("data-modal-url"),
        trigger.getAttribute("data-modal-title") || "Formulario"
      );
      return;
    }

    const btnDetalle = e.target.closest(".js-ver-detalle");
    if (btnDetalle) {
      e.preventDefault();

      if (!detalleModal || !detalleBodyEl) return;

      const url = btnDetalle.getAttribute("data-url");
      if (!url) return;

      if (detalleTitleEl) {
        detalleTitleEl.textContent = "Detalle de compra";
      }

      detalleBodyEl.innerHTML = `<div class="text-muted">Cargando...</div>`;
      detalleModal.show();

      try {
        const res = await fetch(url, {
          method: "GET",
          credentials: "same-origin",
          headers: {
            "X-Requested-With": "XMLHttpRequest",
          },
        });

        const data = await res.json();

        detalleBodyEl.innerHTML =
          data.success && data.html
            ? data.html
            : `<div class="alert alert-danger">No se pudo cargar el detalle.</div>`;
      } catch (error) {
        console.error(error);
        detalleBodyEl.innerHTML = `<div class="alert alert-danger">Error cargando detalle.</div>`;
      }

      return;
    }

    const btnAdd = e.target.closest("#btnAgregarProducto");
    if (btnAdd) {
      e.preventDefault();

      const form = btnAdd.closest("form");
      if (!form) return;

      const container = qs(form, "#productosContainer");
      const template = qs(form, "#emptyFormTemplate");
      const totalForms = qs(form, 'input[name$="-TOTAL_FORMS"]');

      if (!container || !template || !totalForms) return;

      const index = parseInt(totalForms.value || "0", 10);
      const html = template.innerHTML.replace(/__prefix__/g, index);

      container.insertAdjacentHTML("beforeend", html);
      totalForms.value = String(index + 1);

      const newItem = container.lastElementChild;
      const newPrecio = qs(newItem, 'input[name$="-precio_unitario"]');
      attachCOPMask(newPrecio);

      calcularTotal(form);
      validateCompraForm(form);
      return;
    }

    const btnDelete = e.target.closest("#formCompra .btn-eliminar-item");
    if (btnDelete) {
      e.preventDefault();

      const item = btnDelete.closest(".detalle-item");
      const form = btnDelete.closest("form");
      if (!item || !form) return;

      const container = qs(form, "#productosContainer");
      const totalForms = qs(form, 'input[name$="-TOTAL_FORMS"]');
      if (!container || !totalForms) return;

      const anyField = qs(item, "[name]");
      const match = anyField?.name?.match(/^([A-Za-z0-9_]+)-\d+-/);
      const prefix = match ? match[1] : null;

      const deleteInput = qs(item, 'input[name$="-DELETE"]');
      if (deleteInput) {
        deleteInput.checked = true;
        item.classList.add("d-none");
      } else {
        item.remove();
        totalForms.value = String(container.querySelectorAll(".detalle-item").length);
        if (prefix) {
          renumerarForms(container, prefix);
        }
      }

      calcularTotal(form);
      validateCompraForm(form);
      return;
    }

    const btnAnular = e.target.closest(".js-anular-compra");
    if (btnAnular) {
      e.preventDefault();

      const url = btnAnular.getAttribute("data-url");
      const id = btnAnular.getAttribute("data-id");
      if (!url) return;

      const confirm = await Swal.fire({
        title: "¿Anular compra?",
        text: "Esta acción no se puede deshacer.",
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "Sí, anular",
        cancelButtonText: "Cancelar",
      });

      if (!confirm.isConfirmed) return;

      try {
        const result = await fetchSmart(url, {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "X-CSRFToken": csrfFromCookie(),
            "X-Requested-With": "XMLHttpRequest",
          },
        });

        if (result.type !== "json") {
          console.error("Respuesta no JSON al anular compra:", result.data);
          Swal.fire(
            "Error",
            "El servidor respondió con un formato inesperado al anular la compra.",
            "error"
          );
          return;
        }

        const data = result.data;

        if (result.ok && data.success) {
          const fila = document.getElementById(`fila-compra-${id}`);
          const resultados = document.getElementById("compras-resultados");
          const estadoActual = String(resultados?.dataset.estadoActual || "activas").trim();

          if (fila && estadoActual === "todas") {
            renderCompraAnulada(fila);
          } else if (fila) {
            fila.style.transition = "opacity .35s ease, transform .35s ease";
            fila.style.opacity = "0";
            fila.style.transform = "translateX(20px)";
            setTimeout(() => fila.remove(), 350);
          }

          await Swal.fire({
            icon: "success",
            title: "Compra anulada",
            timer: 1200,
            showConfirmButton: false,
          });
        } else {
          Swal.fire(
            "Error",
            data.message || data.detail || `No se pudo anular (HTTP ${result.status}).`,
            "error"
          );
        }
      } catch (error) {
        console.error(error);
        Swal.fire("Error", "Error del servidor.", "error");
      }

      return;
    }
  });

  document.addEventListener("input", (e) => {
    if (
      e.target.matches("#id_proveedor") ||
      e.target.matches('input[name$="-cantidad"]') ||
      e.target.matches('input[name$="-precio_unitario"]')
    ) {
      const form = e.target.closest("form") || document;
      calcularTotal(form);
      validateCompraForm(form);
    }
  });

  document.addEventListener("change", (e) => {
    if (
      e.target.matches("#id_proveedor") ||
      e.target.matches('select[name$="-producto"]') ||
      e.target.matches('input[name$="-cantidad"]') ||
      e.target.matches('input[name$="-precio_unitario"]')
    ) {
      const form = e.target.closest("form") || document;

      if (e.target.matches('input[name$="-precio_unitario"]')) {
        attachCOPMask(e.target);
      }

      calcularTotal(form);
      validateCompraForm(form);
    }
  });

  document.addEventListener("shown.bs.modal", (e) => {
    initCompraForm(e.target);
  });

  document.body.addEventListener("submit", async (e) => {
    const form = e.target.closest("#ajaxFormModal form");
    if (!form) return;

    e.preventDefault();

    let ok = true;

    if (form.id === "formCompra") {
      ok = validateCompraForm(form);
    } else if (form.id === "formDevolucionCompra") {
      ok = window.validateDevolucionForm
        ? window.validateDevolucionForm(form)
        : true;
    }

    if (!ok) return;

    qsa(form, 'input[name$="-precio_unitario"]').forEach((input) => {
      input.value = unformatCOP(input.value);
    });

    const totalInput = qs(form, "#id_precio_total");
    if (totalInput) {
      totalInput.value = unformatCOP(totalInput.value);
    }

    const csrf = csrfFromCookie();
    if (!csrf) return;

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
      if (result.data.success) {
        formModal?.hide();

        await Swal.fire({
          title: "Éxito",
          text: result.data.message || "Guardado correctamente.",
          icon: "success",
          timer: 1400,
          showConfirmButton: false,
        });

        location.reload();
        return;
      }

      formModalBodyEl.innerHTML =
        result.data.html || `<div class="alert alert-danger">No se pudo guardar.</div>`;

      initCompraForm(formModalEl);
      window.initDevolucionForm?.(formModalEl);
      return;
    }

    formModalBodyEl.innerHTML = result.data;
    initCompraForm(formModalEl);
  });

  document.addEventListener("change", async (e) => {
    const input = e.target.closest(".js-reactivar-proveedor-compra");
    if (!input) return;

    if (!input.checked) {
      return;
    }

    const url = input.dataset.reactivarUrl;
    const nombre = input.dataset.proveedorNombre || "este proveedor";
    if (!url) return;

    const confirm = await Swal.fire({
      title: "¿Estás seguro que deseas activar al proveedor?",
      text: `Se activará ${nombre}.`,
      icon: "question",
      showCancelButton: true,
      confirmButtonText: "Sí, activar",
      cancelButtonText: "Cancelar",
      confirmButtonColor: "#4b2f2a",
      cancelButtonColor: "#6c757d",
    });

    if (!confirm.isConfirmed) {
      input.checked = false;
      return;
    }

    const formCompra = document.getElementById("formCompra");
    const selectProveedor = formCompra ? formCompra.querySelector("#id_proveedor") : null;
    const alertaInactivo = document.getElementById("alertaProveedorInactivoCompra");
    const switchHolder = input.closest(".compra-switch-holder");

    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": csrfFromCookie(),
        },
      });

      const data = await response.json().catch(() => ({}));

      if (response.ok && data.success) {
        await Swal.fire({
          title: "Proveedor activado",
          text: data.message || `${nombre} fue activado correctamente.`,
          icon: "success",
          confirmButtonText: "OK",
          confirmButtonColor: "#4b2f2a",
        });
        await Swal.fire({
          title: "Listo",
          text: "Ya puedes continuar editando la compra.",
          icon: "info",
          confirmButtonText: "OK",
          confirmButtonColor: "#4b2f2a",
        });

        if (selectProveedor) {
          selectProveedor.disabled = false;
          const option = selectProveedor.options[selectProveedor.selectedIndex];
          if (option) {
            option.text = option.text.replace(/\s*\(Inactivo\)\s*$/i, "");
          }
          selectProveedor.classList.remove("is-invalid");
        }

        if (alertaInactivo) {
          alertaInactivo.remove();
        }

        if (switchHolder) {
          switchHolder.remove();
        }

        return;
      }

      input.checked = false;
      await Swal.fire({
        title: "Error",
        text: data.message || "No se pudo activar el proveedor.",
        icon: "error",
        confirmButtonText: "OK",
        confirmButtonColor: "#d33",
      });
    } catch (err) {
      console.error("Error activando proveedor desde compras:", err);
      input.checked = false;
      await Swal.fire({
        title: "Error",
        text: "Ocurrió un error al activar el proveedor.",
        icon: "error",
        confirmButtonText: "OK",
        confirmButtonColor: "#d33",
      });
    }
  });
})();
