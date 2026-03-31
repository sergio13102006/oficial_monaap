(() => {
  "use strict";

  const qs = (root, sel) => (root || document).querySelector(sel);

  const RE_NIT = /^[0-9]{7,15}$/;
  const RE_TEL = /^[0-9]{10}$/;
  const RE_DIR = /^.{5,200}$/;
  const RULES = {
    numeric: {
      pattern: /[^\d]/g,
      allow: (text) => /^\d*$/.test(text),
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

  const FIELD_SELECTORS = [
    "#id_nit",
    "#id_nombre_proveedor",
    "#id_telefono_proveedor",
    "#id_correo_proveedor",
    "#id_direccion_proveedor",
    "#id_estado",
  ];

  function getForm(scope) {
    if (!scope) return document.getElementById("proveedorForm");
    if (scope.tagName === "FORM") return scope;
    return qs(scope, "#proveedorForm") || qs(scope, "form");
  }

  function getWrap(input) {
    return input?.closest(".proveedor-input-wrap") || null;
  }

  function getFeedbackEl(input) {
    const wrap = getWrap(input);
    if (!wrap) return null;

    let fb = wrap.parentElement?.querySelector(":scope > .proveedor-field-error");
    if (!fb) {
      fb = document.createElement("div");
      fb.className = "proveedor-field-error";
      wrap.insertAdjacentElement("afterend", fb);
    }
    return fb;
  }

  function getRule(input) {
    if (!input) return null;
    const rule = (input.dataset.validate || "").trim();
    return RULES[rule] ? rule : null;
  }

  function sanitizeInput(input) {
    if (!input) return;

    const rule = getRule(input);
    if (!rule) return;

    const cleaned = String(input.value || "").replace(RULES[rule].pattern, "");
    if (cleaned !== input.value) {
      input.value = cleaned;
    }
  }

  function bindGuards(form) {
    const fields = form.querySelectorAll("[data-validate]");
    fields.forEach((input) => {
      if (input.dataset.guardWired === "1") return;
      input.dataset.guardWired = "1";

      input.addEventListener("beforeinput", (e) => {
        if (!e.inputType || !e.inputType.startsWith("insert")) return;
        const rule = getRule(input);
        if (!rule) return;
        const data = e.data || "";
        if (!RULES[rule].allow(data)) {
          e.preventDefault();
        }
      });

      input.addEventListener("paste", (e) => {
        const rule = getRule(input);
        if (!rule) return;
        const pasted = e.clipboardData?.getData("text") || "";
        if (!RULES[rule].allow(pasted)) {
          e.preventDefault();
          sanitizeInput(input);
        }
      });

      input.addEventListener("input", () => sanitizeInput(input));
    });
  }

  function clearState(input) {
    if (!input) return;

    input.classList.remove("is-valid", "is-invalid");

    const wrap = getWrap(input);
    if (wrap) {
      wrap.classList.remove("is-ok", "is-error", "has-error");
    }

    const fb = getFeedbackEl(input);
    if (fb) {
      fb.textContent = "";
      fb.classList.remove("is-visible");
    }
  }

  function markValid(input) {
    if (!input) return;

    clearState(input);
    input.classList.add("is-valid");

    const wrap = getWrap(input);
    if (wrap) {
      wrap.classList.add("is-ok");
    }
  }

  function markInvalid(input, message) {
    if (!input) return;

    clearState(input);
    input.classList.add("is-invalid");

    const wrap = getWrap(input);
    if (wrap) {
      wrap.classList.add("is-error");
    }

    const fb = getFeedbackEl(input);
    if (fb) {
      fb.textContent = message || "Campo inválido";
      fb.classList.add("is-visible");
    }
  }

  function isEmailValid(value) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
  }

  function getProveedorId(form) {
    return (form?.dataset?.proveedorId || "").trim();
  }

  async function checkDuplicateNombre(form, input) {
    if (!form || !input) return true;

    const value = (input.value || "").trim();
    if (!value) return true;

    const currentId = getProveedorId(form);
    const endpoint = (form?.dataset?.proveedorValidarUrl || "").trim();
    if (!endpoint) return true;
    const url = new URL(endpoint, window.location.origin);
    url.searchParams.set("nombre", value);
    if (currentId) url.searchParams.set("proveedor_id", currentId);

    const token = String(Date.now()) + Math.random().toString(36).slice(2);
    input.dataset.nombreCheckToken = token;

    try {
      const response = await fetch(url.toString(), {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      const data = await response.json().catch(() => ({}));

      if (input.dataset.nombreCheckToken !== token) return false;

      if (!data.valid) {
        input.dataset.nombreDuplicado = "1";
        markInvalid(input, data.message || "Ya existe un proveedor con este nombre.");
        validateProveedorForm(form);
        return false;
      }

      delete input.dataset.nombreDuplicado;
      if ((value.length >= 3) || !input.hasAttribute("required")) {
        markValid(input);
      } else {
        clearState(input);
      }
      validateProveedorForm(form);
      return true;
    } catch (error) {
      return true;
    }
  }

  function wireNombreDuplicado(form) {
    const input = qs(form, "#id_nombre_proveedor");
    if (!input || input.dataset.nombreDupWired === "1") return;
    input.dataset.nombreDupWired = "1";

    let timer = null;
    const schedule = () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        const value = (input.value || "").trim();
        if (!value || value.length < 3) return;
        checkDuplicateNombre(form, input);
      }, 350);
    };

    input.addEventListener("input", schedule);
    input.addEventListener("blur", schedule);
  }

  function validateField(input, { force = false } = {}) {
    if (!input) return true;

    const value = (input.value || "").trim();
    let message = "";
    const isEmpty = value === "";
    const isRequired = input.hasAttribute("required");

    if (isEmpty && !force) {
      clearState(input);
      return true;
    }

    switch (input.id) {
      case "id_nit":
        if (!input.hasAttribute("maxlength")) input.setAttribute("maxlength", "15");
        if (!value) message = "NIT obligatorio";
        else if (!RE_NIT.test(value)) message = "NIT debe tener entre 7 y 15 digitos";
        break;

      case "id_nombre_proveedor":
        if (!value) message = "Nombre obligatorio";
        else if (value.length < 3) message = "Mínimo 3 letras";
        else if (input.dataset.nombreDuplicado === "1") message = "Ya existe un proveedor con este nombre.";
        break;

      case "id_telefono_proveedor":
        if (!input.hasAttribute("maxlength")) input.setAttribute("maxlength", "10");
        if (!value) message = "Teléfono obligatorio";
        else if (!RE_TEL.test(value)) message = "Teléfono debe tener exactamente 10 digitos";
        break;

      case "id_correo_proveedor":
        if (!value) message = "Correo obligatorio";
        else if (!isEmailValid(value)) message = "Correo inválido";
        break;

      case "id_direccion_proveedor":
        if (!value) message = "Dirección obligatoria";
        else if (!RE_DIR.test(value)) message = "Mínimo 5 caracteres";
        break;

      case "id_estado":
        if (!value) message = "Selecciona un estado";
        break;

      default:
        if (input.hasAttribute("required") && !value) {
          message = "Campo obligatorio";
        }
    }

    if (message) {
      markInvalid(input, message);
      return false;
    }

    if (isRequired || value) {
      markValid(input);
    } else {
      clearState(input);
    }
    return true;
  }

  function getSubmitButton(form) {
    return qs(form, "#btnGuardarProveedor") || qs(form, 'button[type="submit"]');
  }

  function validateProveedorForm(scope, { force = false } = {}) {
    const form = getForm(scope);
    if (!form) return true;

    let isValid = true;
    let hasPendingRequired = false;

    FIELD_SELECTORS.forEach((selector) => {
      const field = qs(form, selector);
      if (!field) return;

      const value = (field.value || "").trim();
      if (!value && !force && field.hasAttribute("required")) {
        clearState(field);
        hasPendingRequired = true;
        return;
      }

      if (!validateField(field, { force })) {
        isValid = false;
      }
    });

    const btn = getSubmitButton(form);
    if (btn) btn.disabled = !isValid || hasPendingRequired;

    return isValid && !hasPendingRequired;
  }

  function wire(scope) {
    const form = getForm(scope);
    if (!form) return;

    if (form.dataset.wiredProveedor === "1") {
      validateProveedorForm(form);
      return;
    }

    form.dataset.wiredProveedor = "1";
    bindGuards(form);
    wireNombreDuplicado(form);

    FIELD_SELECTORS.forEach((selector) => {
      const field = qs(form, selector);
      if (!field) return;

      if (field.id === "id_telefono_proveedor") {
        field.setAttribute("maxlength", "10");
      } else if (field.id === "id_nit") {
        field.setAttribute("maxlength", "15");
      }

      field.addEventListener("input", () => {
        if (field.id === "id_telefono_proveedor" && field.value.length > 10) {
          field.value = field.value.slice(0, 10);
        } else if (field.id === "id_nit" && field.value.length > 15) {
          field.value = field.value.slice(0, 15);
        }
        field.dataset.touched = "1";
        validateProveedorForm(form);
      });
      field.addEventListener("change", () => {
        field.dataset.touched = "1";
        validateProveedorForm(form);
      });
      field.addEventListener("blur", () => validateProveedorForm(form));
    });

    form.addEventListener("submit", (e) => {
      if (!validateProveedorForm(form, { force: true })) {
        e.preventDefault();
        e.stopPropagation();
      }
    });

    validateProveedorForm(form);
  }

  window.ProveedorFormulario = {
    init(scope) {
      wire(scope || document);
    },
    validate(scope) {
      return validateProveedorForm(scope || document, { force: true });
    }
  };

  document.addEventListener("DOMContentLoaded", () => {
    wire(document);
  });

  document.addEventListener("shown.bs.modal", (e) => {
    wire(e.target);
  });
})();
