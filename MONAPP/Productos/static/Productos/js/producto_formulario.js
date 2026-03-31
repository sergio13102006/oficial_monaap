(() => {
  // =========================
  // Helpers
  // =========================
  const qs = (root, sel) => (root || document).querySelector(sel);

  // =========================
  // Helpers dinero
  // =========================
  function onlyDigits(value) {
    return String(value || "").replace(/\D/g, "");
  }

  function formatMiles(value) {
    const digits = onlyDigits(value);
    if (!digits) return "";
    return new Intl.NumberFormat("es-CO", {
      maximumFractionDigits: 0,
    }).format(Number(digits));
  }

  function normalizeMoneyForSubmit(value) {
    return onlyDigits(value);                                                                 
  }

  function formatMoneyInput(input) {
    if (!input) return;
    input.value = formatMiles(input.value);
  }

  const RULES = {
    numeric: {
      pattern: /[^\d]/g,
      allow: (text) => /^\d*$/.test(text),
    },
    money: {
      pattern: /[^\d.,\s]/g,
      allow: (text) => /^[\d.,\s]*$/.test(text),
    },
    alpha: {
      pattern: /[^\p{L}\s]/gu,
      allow: (text) => /^[\p{L}\s]*$/u.test(text),
    },
    alnum: {
      pattern: /[^\p{L}\p{N}\s]/gu,
      allow: (text) => /^[\p{L}\p{N}\s]*$/u.test(text),
    },
    text: {
      pattern: /[<>]/g,
      allow: (text) => !/[<>]/.test(text),
    },
  };

  function getValidationRule(input) {
    if (!input) return null;
    const rule = (input.dataset.validate || "").trim();
    if (rule && RULES[rule]) return rule;
    return null;
  }

  function sanitizeRestrictedInput(input) {
    if (!input || input.type === "file") return;

    if (input.dataset.formatMoney === "1") {
      const raw = String(input.value || "");
      input.value = raw.replace(RULES.money.pattern, "");
      return;
    }

    const rule = getValidationRule(input);
    if (!rule) return;

    const cleaned = String(input.value || "").replace(RULES[rule].pattern, "");
    if (cleaned !== input.value) {
      input.value = cleaned;
    }
  }

  function bindRestrictionGuards(form) {
    const inputs = form.querySelectorAll("[data-validate], [data-format-money='1']");
    inputs.forEach((input) => {
      if (input.dataset.guardWired === "1") return;
      input.dataset.guardWired = "1";

      input.addEventListener("beforeinput", (e) => {
        if (input.type === "file") return;
        if (!e.inputType || !e.inputType.startsWith("insert")) return;

        const rule = input.dataset.formatMoney === "1" ? "money" : getValidationRule(input);
        if (!rule) return;

        const data = e.data || "";
        const allowed = RULES[rule].allow(data);
        if (!allowed) e.preventDefault();
      });

      input.addEventListener("paste", (e) => {
        const rule = input.dataset.formatMoney === "1" ? "money" : getValidationRule(input);
        if (!rule) return;

        const pasted = e.clipboardData?.getData("text") || "";
        const allowed = RULES[rule].allow(pasted);
        if (!allowed) {
          e.preventDefault();
          sanitizeRestrictedInput(input);
        }
      });

      input.addEventListener("input", () => sanitizeRestrictedInput(input));
    });
  }

  // =========================
  // Modal AJAX genérico
  // =========================
  document.addEventListener("DOMContentLoaded", () => {
    const modalEl = document.getElementById("ajaxFormModal");
    const modalTitleEl = document.getElementById("ajaxFormModalTitle");
    const modalBodyEl = document.getElementById("ajaxFormModalBody");
    if (!modalEl || !modalTitleEl || !modalBodyEl) return;

    const modal = new bootstrap.Modal(modalEl);

    async function fetchSmart(url, options = {}) {
      const res = await fetch(url, options);
      const contentType = (res.headers.get("content-type") || "").toLowerCase();

      if (contentType.includes("application/json")) {
        const data = await res.json();
        return { type: "json", ok: res.ok, status: res.status, data };
      }

      const text = await res.text();
      return { type: "html", ok: res.ok, status: res.status, data: text };
    }

    async function openModal(url, title) {
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
        ProductoFormulario.init(modalEl);
        return;
      }

      modalBodyEl.innerHTML = result.data;
      ProductoFormulario.init(modalEl);
    }

    document.addEventListener("click", (e) => {
      const trigger = e.target.closest("[data-modal-url]");
      if (!trigger) return;
      e.preventDefault();

      openModal(
        trigger.getAttribute("data-modal-url"),
        trigger.getAttribute("data-modal-title") || "Formulario"
      );
    });

    document.addEventListener("submit", async (e) => {
      const form = e.target.closest("#ajaxFormModal form");
      if (!form) return;

      e.preventDefault();

      const nombreOk = await ProductoFormulario.validateNombre(form, { force: true });
      const ok = ProductoFormulario.validate(form);
      if (!ok || !nombreOk) return;

      const url = form.action;

      // ✅ limpiar formato visual antes de enviar
      const precioInput = qs(form, "#id_precio");
      if (precioInput) {
        precioInput.value = normalizeMoneyForSubmit(precioInput.value);
      }

      const formData = new FormData(form);
      const csrf = form.querySelector('input[name="csrfmiddlewaretoken"]')?.value || "";

      const result = await fetchSmart(url, {
        method: "POST",
        body: formData,
        credentials: "same-origin",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": csrf,
        },
      });

      if (result.type === "json") {
        if (result.data.success) {
          modal.hide();
          window.location.reload();
          return;
        }

        modalTitleEl.textContent = result.data.title || modalTitleEl.textContent;
        modalBodyEl.innerHTML =
          result.data.html || `<div class="alert alert-danger mb-0">No se pudo guardar.</div>`;

        ProductoFormulario.init(modalEl);
        return;
      }

      modalBodyEl.innerHTML = result.data;
      ProductoFormulario.init(modalEl);
    });
  });

  // =========================
  // UI validación nueva
  // =========================
  function getWrap(input) {
    return input?.closest(".producto-input-wrap") || null;
  }

  function ensureWrapper(input) {
    if (!input || input.type === "file") return null;

    const existing = getWrap(input);
    if (existing) return existing;

    const target =
      input.closest(".select-pro") ||
      input.closest(".input-group") ||
      input;

    const parent = target.parentElement;
    if (!parent) return null;

    const wrap = document.createElement("div");
    wrap.className = "producto-input-wrap";

    parent.insertBefore(wrap, target);
    wrap.appendChild(target);

    const ok = document.createElement("span");
    ok.className = "producto-valid-icon";
    ok.innerHTML = `<i class="bi bi-check-lg"></i>`;

    const bad = document.createElement("span");
    bad.className = "producto-invalid-icon";
    bad.innerHTML = `<i class="bi bi-exclamation-circle-fill"></i>`;

    wrap.appendChild(ok);
    wrap.appendChild(bad);

    const fb = document.createElement("div");
    fb.className = "producto-field-error";
    wrap.insertAdjacentElement("afterend", fb);

    return wrap;
  }

  function getFeedbackEl(input) {
    const wrap = getWrap(input) || ensureWrapper(input);
    if (!wrap) return null;

    let fb = wrap.nextElementSibling;
    if (!fb || !fb.classList.contains("producto-field-error")) {
      fb = document.createElement("div");
      fb.className = "producto-field-error";
      wrap.insertAdjacentElement("afterend", fb);
    }
    return fb;
  }

  function clearState(input) {
    if (!input) return;

    input.classList.remove("is-valid", "is-invalid");
    input.style.backgroundImage = "none";
    input.style.boxShadow = "none";

    const wrap = getWrap(input);
    if (wrap) {
      wrap.classList.remove("is-ok", "is-error");
    }

    const fb = getFeedbackEl(input);
    if (fb) {
      fb.textContent = "";
      fb.classList.remove("is-visible");
    }
  }

  function markValid(input) {
    if (!input) return;

    const isRequired = input.hasAttribute("required");
    const val = (input.value || "").trim();

    if (!isRequired && !val) {
      clearState(input);
      return;
    }

    input.classList.remove("is-invalid");
    input.classList.add("is-valid");
    input.style.backgroundImage = "none";

    const wrap = getWrap(input) || ensureWrapper(input);
    if (wrap) {
      wrap.classList.remove("is-error");
      wrap.classList.add("is-ok");
    }

    const fb = getFeedbackEl(input);
    if (fb) {
      fb.textContent = "";
      fb.classList.remove("is-visible");
    }
  }

  function markInvalid(input, msg) {
    if (!input) return;

    input.classList.remove("is-valid");
    input.classList.add("is-invalid");
    input.style.backgroundImage = "none";

    const wrap = getWrap(input) || ensureWrapper(input);
    if (wrap) {
      wrap.classList.remove("is-ok");
      wrap.classList.add("is-error");
    }

    const fb = getFeedbackEl(input);
    if (fb) {
      fb.textContent = msg || "Campo inválido";
      fb.classList.add("is-visible");
    }
  }
  // =========================
  // Preview imagen
  // =========================
  function updatePreview(form) {
    const imgInput = qs(form, "#id_imagen");
    const imgEl = qs(form, "#previewProductoImagen");
    const msgEl = qs(form, "#previewProductoImagenMsg");
    const emptyEl = qs(form, "#previewEmpty");
    const dzFilename = qs(form, "#dzFilename");
    const removeBtn = qs(form, "#imgPreviewRemove");

    if (!imgEl) return;

    const file = imgInput?.files?.[0];

    const initialSrc = (imgEl.dataset.initialSrc || "").trim();
    const clearCheckbox = qs(form, "#id_imagen-clear");
    const isCleared = clearCheckbox ? clearCheckbox.checked : false;

    // reset UI
    imgEl.style.display = "none";
    imgEl.removeAttribute("src");
    if (msgEl) msgEl.textContent = "";
    if (emptyEl) emptyEl.style.display = "block";
    if (dzFilename) dzFilename.textContent = "Ningún archivo seleccionado";
    if (removeBtn) removeBtn.classList.add("d-none");

    // 1) archivo
    if (file) {
      if (!file.type.startsWith("image/")) {
        if (msgEl) msgEl.textContent = "El archivo seleccionado no es una imagen.";
        return;
      }

      if (clearCheckbox) clearCheckbox.checked = false;

      const blobUrl = URL.createObjectURL(file);
      imgEl.src = blobUrl;
      imgEl.style.display = "block";
      if (emptyEl) emptyEl.style.display = "none";
      if (dzFilename) dzFilename.textContent = file.name;
      if (msgEl) msgEl.textContent = file.name;
      if (removeBtn) removeBtn.classList.remove("d-none");

      imgEl.onload = () => URL.revokeObjectURL(blobUrl);
      return;
    }

    // 2) imagen inicial (editar)
    if (initialSrc && !isCleared) {
      imgEl.src = initialSrc;
      imgEl.style.display = "block";
      if (emptyEl) emptyEl.style.display = "none";
      if (msgEl) msgEl.textContent = "Imagen actual";
      if (removeBtn) removeBtn.classList.remove("d-none");
    }
  }

  // =========================
  // Validación
  // =========================
  function showGeneralErrors(form, messages = []) {
    const box = qs(form, "#productoErroresGenerales");
    if (!box) return;

    if (!messages.length) {
      box.classList.add("d-none");
      box.innerHTML = "";
      return;
    }

    box.classList.remove("d-none");
    box.innerHTML = `
      <strong>Revisa estos campos:</strong>
      <ul class="mb-0 mt-2">
        ${messages.map((m) => `<li>${m}</li>`).join("")}
      </ul>
    `;
  }

  const RE_SOLO_LETRAS = /^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ\s]+$/;
  const RE_SOLO_NUMEROS = /^\d+$/;
  const RE_NOMBRE_PRODUCTO = /^[\p{L}\p{N}\s]+$/u;

  function getProductoCodigo(form) {
    return (form?.dataset?.productoCodigo || "").trim();
  }

  function setNombreDuplicado(input, duplicado) {
    if (!input) return;
    input.dataset.nombreDuplicado = duplicado ? "1" : "0";
  }

  async function validarNombreProductoUnico(form, { force = false } = {}) {
    const nombre = qs(form, "#id_nombre");
    if (!nombre) return true;

    const valor = (nombre.value || "").trim();
    const productoCodigo = getProductoCodigo(form);

    if (!valor) {
      setNombreDuplicado(nombre, false);
      if (force) {
        markInvalid(nombre, "Nombre obligatorio");
      } else {
        clearState(nombre);
      }
      return false;
    }

    if (valor.length < 3) {
      setNombreDuplicado(nombre, false);
      markInvalid(nombre, "Debe tener al menos 3 caracteres");
      return false;
    }

    if (!RE_NOMBRE_PRODUCTO.test(valor)) {
      setNombreDuplicado(nombre, false);
      markInvalid(nombre, "El nombre solo puede contener letras, números y espacios.");
      return false;
    }

    setNombreDuplicado(nombre, false);

    const controller = new AbortController();
    if (nombre._nombreAbortController) {
      nombre._nombreAbortController.abort();
    }
    nombre._nombreAbortController = controller;

    try {
      const url = new URL("/Productos/validar-nombre/", window.location.origin);
      url.searchParams.set("nombre", valor);
      if (productoCodigo) {
        url.searchParams.set("producto_id", productoCodigo);
      }

      const res = await fetch(url.toString(), {
        headers: { "X-Requested-With": "XMLHttpRequest" },
        signal: controller.signal,
      });

      const data = await res.json();

      if (!data.valido) {
        setNombreDuplicado(nombre, true);
        markInvalid(nombre, data.mensaje || "Nombre no válido.");
        return false;
      }

      setNombreDuplicado(nombre, false);
      markValid(nombre);
      return true;
    } catch (error) {
      if (error.name !== "AbortError") {
        console.error("Error validando nombre de producto:", error);
      }
      return !nombre.classList.contains("is-invalid");
    } finally {
      if (nombre._nombreAbortController === controller) {
        nombre._nombreAbortController = null;
      }
    }
  }

  function validateProductoForm(scope, { force = false } = {}) {
    const form =
      scope?.tagName === "FORM"
        ? scope
        : qs(scope, "form.producto-form") || qs(scope, "#productoForm") || qs(scope, "form");

    if (!form) return true;

    const errores = [];
    let tienePendientes = false;

    const marca = qs(form, "#id_marca");
    const nombre = qs(form, "#id_nombre");
    const precio = qs(form, "#id_precio");
    const unidad = qs(form, "#id_unidad_medida");
    const linea = qs(form, "#id_linea");
    const presentacion = qs(form, "#id_presentacion");
    const imgInput = qs(form, "#id_imagen");

    if (nombre) {
      const v = (nombre.value || "").trim();
      const nombreDuplicado = nombre.dataset.nombreDuplicado === "1";
      if (!v && !force) {
        setNombreDuplicado(nombre, false);
        clearState(nombre);
        tienePendientes = true;
      } else if (!v) {
        errores.push("El nombre del producto es obligatorio.");
        markInvalid(nombre, "Nombre obligatorio");
      } else if (nombreDuplicado) {
        errores.push("Ya existe un producto con este nombre.");
        markInvalid(nombre, "Ya existe un producto con este nombre.");
      } else if (!RE_NOMBRE_PRODUCTO.test(v)) {
        errores.push("El nombre solo puede contener letras, números y espacios.");
        markInvalid(nombre, "Solo letras, números y espacios");
      } else if (v.length < 3) {
        errores.push("El nombre debe tener al menos 3 caracteres.");
        markInvalid(nombre, "Mínimo 3 caracteres");
      } else markValid(nombre);
    }

    if (marca) {
      const v = (marca.value || "").trim();
      if (!v && !force) {
        clearState(marca);
        tienePendientes = true;
      } else if (!v) {
        errores.push("La marca es obligatoria.");
        markInvalid(marca, "Marca obligatoria");
      } else markValid(marca);
    }

    if (precio) {
      const copPrev = qs(form, "#cop_preview_producto");
      const raw = String(precio.value || "").replace(/\./g, "").replace(",", ".");
      const n = parseFloat(raw);
      let msg = "";

      if (!String(precio.value || "").trim()) {
        if (force) msg = "Precio obligatorio";
        else { clearState(precio); if(copPrev) copPrev.classList.remove("visible"); tienePendientes = true; }
      } else if (isNaN(n) || n < 100) {
        msg = "Mínimo $100";
      } else if (n > 99999999) {
        msg = "Máximo $99.999.999";
      }

      if (msg) {
        errores.push(msg);
        markInvalid(precio, msg);
        if (copPrev) copPrev.classList.remove("visible");
      } else if (String(precio.value || "").trim()) {
        markValid(precio);
        if (copPrev) {
          copPrev.textContent = formatMiles(raw) ? "$ " + formatMiles(raw) : "";
          copPrev.classList.add("visible");
        }
      }
    }

    if (unidad && unidad.hasAttribute("required")) {
      if (!unidad.value && !force) {
        clearState(unidad);
        tienePendientes = true;
      } else if (!unidad.value) {
        errores.push("La unidad de medida es obligatoria.");
        markInvalid(unidad, "Obligatoria");
      } else markValid(unidad);
    } else if (unidad) {
      const v = (unidad.value || "").trim();
      if (v) markValid(unidad);
      else clearState(unidad);
    }

    if (linea) {
      const v = (linea.value || "").trim();

      if (!v && !force) {
        clearState(linea);
        tienePendientes = true;
      } else if (!v) {
        errores.push("La línea es obligatoria.");
        markInvalid(linea, "Obligatoria");
      } else if (!RE_SOLO_LETRAS.test(v)) {
        errores.push("La línea solo debe contener letras.");
        markInvalid(linea, "Solo letras");
      } else {
        markValid(linea);
      }
    }

    if (presentacion) {
      const v = (presentacion.value || "").trim();

      if (!v && !force) {
        clearState(presentacion);
        tienePendientes = true;
      } else if (!v) {
        errores.push("La presentación es obligatoria.");
        markInvalid(presentacion, "Obligatoria");
      } else if (!RE_SOLO_NUMEROS.test(v)) {
        errores.push("La presentación solo debe contener números.");
        markInvalid(presentacion, "Solo números");
      } else {
        markValid(presentacion);
      }
    }

    if (imgInput?.files?.length) {
      const file = imgInput.files[0];
      if (!file.type.startsWith("image/")) {
        errores.push("El archivo seleccionado no es una imagen.");
        markInvalid(imgInput, "Archivo inválido");
      } else markValid(imgInput);
    } else if (imgInput) {
      clearState(imgInput);
    }

    showGeneralErrors(form, errores);

    const btn = qs(form, "#btnGuardarProducto") || qs(form, 'button[type="submit"]');
    if (btn) btn.disabled = errores.length > 0 || tienePendientes;

    return errores.length === 0 && !tienePendientes;
  }

  // =========================
  // Pastilla Estado (Inactivo/Activo)
  // =========================
  function wireEstadoPill(form) {
    const pill = qs(form, "#estadoPill");
    if (!pill || pill.dataset.wired === "1") return;
    pill.dataset.wired = "1";

    const checkbox = pill.querySelector('input[type="checkbox"]');
    const btns = Array.from(pill.querySelectorAll(".estado-opt"));
    if (!checkbox || !btns.length) return;

    const sync = () => {
      const on = checkbox.checked;
      btns.forEach((b) => {
        const isOnBtn = b.dataset.val === "1";
        b.classList.toggle("is-active", (on && isOnBtn) || (!on && !isOnBtn));
      });
    };

    btns.forEach((b) => {
      b.addEventListener("click", () => {
        checkbox.checked = b.dataset.val === "1";
        checkbox.dispatchEvent(new Event("change", { bubbles: true }));
        sync();
      });
    });

    checkbox.addEventListener("change", sync);
    sync();
  }

  // =========================
  // Wire events (1 sola vez)
  // =========================
  function wireEvents(scope) {
    const root = scope || document;
    const form =
      qs(root, "form.producto-form") || qs(root, "#productoForm") || qs(root, "form");
    if (!form) return;

    if (form.dataset.wired === "1") {
      updatePreview(form);
      validateProductoForm(form);
      return;
    }
    form.dataset.wired = "1";

    bindRestrictionGuards(form);

    let nombreTimer = null;

    ["#id_nombre", "#id_marca", "#id_precio", "#id_unidad_medida", "#id_linea", "#id_presentacion"].forEach((sel) => {
      const el = qs(form, sel);
      if (el) ensureWrapper(el);
    });
    // X quitar imagen
    const removeBtn = qs(form, "#imgPreviewRemove");
    if (removeBtn) {
      removeBtn.addEventListener("click", () => {
        const imgEl = qs(form, "#previewProductoImagen");
        const imgInput = qs(form, "#id_imagen");
        const clearCheckbox = qs(form, "#id_imagen-clear");

        if (imgInput) imgInput.value = "";
        if (clearCheckbox) clearCheckbox.checked = true;

        // para que no vuelva a aparecer en UI
        if (imgEl) imgEl.dataset.initialSrc = "";

        updatePreview(form);
        validateProductoForm(form);
      });
    }

    form.addEventListener("input", (e) => {
      
      const t = e.target;
      sanitizeRestrictedInput(t);
      if(t.matches("#id_precio")){
        formatMoneyInput(t);
      }
      if (
        t.matches("#id_nombre") ||
        t.matches("#id_marca") ||
        t.matches("#id_precio") ||
        t.matches("#id_linea") ||
        t.matches("#id_presentacion")
      ) {
        if (t.matches("#id_nombre")) {
          setNombreDuplicado(t, false);
          if (nombreTimer) clearTimeout(nombreTimer);
          nombreTimer = setTimeout(() => {
            validarNombreProductoUnico(form);
          }, 350);
        }
        validateProductoForm(form);
      }
    });

    form.addEventListener("change", (e) => {
      const t = e.target;

      if (t.matches("#id_unidad_medida, #id_linea, #id_presentacion")) {
        validateProductoForm(form);
      }
      if (t.matches("#id_nombre")) {
        setNombreDuplicado(t, false);
        if (nombreTimer) clearTimeout(nombreTimer);
        validarNombreProductoUnico(form, { force: true });
      }
      if (t.matches("#id_imagen")) {
        const clearCheckbox = qs(form, "#id_imagen-clear");

        if (clearCheckbox && t.files?.length) clearCheckbox.checked = false;

        updatePreview(form);
        validateProductoForm(form);
      }
    });

    wireEstadoPill(form);
    updatePreview(form);
    validateProductoForm(form);
  }

  // =========================
  // Public API
  // =========================
  window.ProductoFormulario = {
    init(scope) {
      wireEvents(scope || document);
    },
    validate(scope) {
      return validateProductoForm(scope || document, { force: true });
    },
    validateNombre(scope, options = {}) {
      const form =
        scope?.tagName === "FORM"
          ? scope
          : qs(scope, "form.producto-form") || qs(scope, "#productoForm") || qs(scope, "form");
      return validarNombreProductoUnico(form || document, options);
    },
  };

  document.addEventListener("DOMContentLoaded", () => ProductoFormulario.init(document));
  document.addEventListener("shown.bs.modal", (e) => ProductoFormulario.init(e.target));
})();
