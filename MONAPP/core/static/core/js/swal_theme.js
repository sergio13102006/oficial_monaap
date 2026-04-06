(function () {
  function injectStyles() {
    if (document.getElementById("mk-swal-theme-styles")) return;

    const style = document.createElement("style");
    style.id = "mk-swal-theme-styles";
    style.textContent = `
      .mk-swal-popup {
        border-radius: 22px !important;
        border: 1px solid rgba(111, 71, 45, 0.14) !important;
        box-shadow: 0 24px 60px rgba(18, 11, 10, 0.28) !important;
        padding: 1.45rem 1.35rem 1.2rem !important;
      }
      .mk-swal-title {
        color: #2f1d18 !important;
        font-weight: 800 !important;
        letter-spacing: 0.01em !important;
      }
      .mk-swal-html,
      .mk-swal-html-container {
        color: #5a463d !important;
        font-size: 0.98rem !important;
        line-height: 1.55 !important;
      }
      .mk-swal-actions {
        gap: 10px !important;
        margin-top: 1rem !important;
      }
      .mk-swal-confirm,
      .mk-swal-deny,
      .mk-swal-cancel {
        min-width: 132px !important;
        min-height: 42px !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        box-shadow: 0 10px 22px rgba(8, 4, 3, 0.22) !important;
      }
      .mk-swal-confirm.btn-primary {
        background: linear-gradient(135deg, #3a2a24 0%, #1f1412 100%) !important;
        border: 1px solid #2a1d18 !important;
        color: #fff !important;
      }
      .mk-swal-deny.btn-success {
        background: linear-gradient(135deg, #8a6848 0%, #5f4530 100%) !important;
        border: 1px solid #4d3524 !important;
        color: #fff !important;
      }
      .mk-swal-confirm.btn-danger {
        background: linear-gradient(135deg, #8b332d 0%, #5f1d1a 100%) !important;
        border: 1px solid #4d1614 !important;
        color: #fff !important;
      }
      .mk-swal-cancel.btn-outline-secondary {
        border: 1px solid rgba(111, 71, 45, 0.24) !important;
        color: #4a352f !important;
        background: #fffaf6 !important;
      }
      .swal2-icon.swal2-success [class^='swal2-success-line'],
      .swal2-icon.swal2-success .swal2-success-ring {
        border-color: #7a4e37 !important;
      }
      .swal2-icon.swal2-success .swal2-success-line-tip,
      .swal2-icon.swal2-success .swal2-success-line-long {
        background-color: #7a4e37 !important;
      }
      .swal2-icon.swal2-warning {
        border-color: #ad7a3c !important;
        color: #ad7a3c !important;
      }
      .swal2-icon.swal2-error {
        border-color: #8b332d !important;
        color: #8b332d !important;
      }
    `;
    document.head.appendChild(style);
  }

  function normalizeArgs(args) {
    if (args.length === 1 && typeof args[0] === "object" && args[0] !== null) {
      return { ...(args[0] || {}) };
    }

    if (args.length >= 3) {
      return {
        title: args[0],
        text: args[1],
        icon: args[2],
      };
    }

    if (args.length === 2) {
      return {
        title: args[0],
        text: args[1],
      };
    }

    if (args.length === 1) {
      return { title: args[0] };
    }

    return {};
  }

  function detectCrudMode(options) {
    const haystack = [
      options.title,
      options.text,
      options.html,
      options.confirmButtonText,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();

    if (/(eliminar|borrar|anular|quitar|remover)/.test(haystack)) return "delete";
    if (/(editar|guardar cambios|actualizar|modificar)/.test(haystack)) return "edit";
    if (/(crear|registrar|guardar|agregar|nuevo)/.test(haystack)) return "create";
    return "default";
  }

  function normalizeOptions(rawOptions) {
    const options = { ...rawOptions };
    const mode = detectCrudMode(options);
    const destructive =
      mode === "delete" ||
      options.icon === "warning" ||
      options.icon === "error";

    options.buttonsStyling = false;
    options.reverseButtons = typeof options.reverseButtons === "boolean" ? options.reverseButtons : true;

    const customClass = { ...(options.customClass || {}) };
    customClass.popup = [customClass.popup, "mk-swal-popup"].filter(Boolean).join(" ");
    customClass.title = [customClass.title, "mk-swal-title"].filter(Boolean).join(" ");
    customClass.htmlContainer = [customClass.htmlContainer, "mk-swal-html-container"].filter(Boolean).join(" ");
    customClass.actions = [customClass.actions, "mk-swal-actions"].filter(Boolean).join(" ");
    customClass.confirmButton = [
      customClass.confirmButton,
      "mk-swal-confirm",
      destructive ? "btn btn-danger" : "btn btn-primary",
    ]
      .filter(Boolean)
      .join(" ");
    customClass.denyButton = [
      customClass.denyButton,
      "mk-swal-deny btn btn-success",
    ]
      .filter(Boolean)
      .join(" ");
    customClass.cancelButton = [
      customClass.cancelButton,
      "mk-swal-cancel btn btn-outline-secondary",
    ]
      .filter(Boolean)
      .join(" ");
    options.customClass = customClass;

    if (!options.confirmButtonText && options.showConfirmButton !== false) {
      if (mode === "delete") {
        options.confirmButtonText = "Sí, eliminar";
      } else if (mode === "edit") {
        options.confirmButtonText = "Guardar cambios";
      } else if (mode === "create") {
        options.confirmButtonText = "Guardar";
      } else {
        options.confirmButtonText = "Aceptar";
      }
    }

    if (options.showCancelButton && !options.cancelButtonText) {
      options.cancelButtonText = "Cancelar";
    }

    if (options.showCancelButton && typeof options.focusCancel !== "boolean") {
      options.focusCancel = true;
    }

    return options;
  }

  function patchSwal() {
    if (typeof window.Swal === "undefined" || window.Swal.__mkThemePatched) return;

    injectStyles();

    const originalFire = window.Swal.fire.bind(window.Swal);
    const originalMixin = window.Swal.mixin ? window.Swal.mixin.bind(window.Swal) : null;

    window.Swal.fire = function (...args) {
      const normalized = normalizeOptions(normalizeArgs(args));
      return originalFire(normalized);
    };

    if (originalMixin) {
      window.Swal.mixin = function (mixinOptions = {}) {
        const mixed = originalMixin(normalizeOptions(mixinOptions));
        if (mixed && typeof mixed.fire === "function") {
          const mixedOriginalFire = mixed.fire.bind(mixed);
          mixed.fire = function (...args) {
            const normalized = normalizeOptions(normalizeArgs(args));
            return mixedOriginalFire(normalized);
          };
        }
        return mixed;
      };
    }

    window.MonakeratinaSwal = {
      fire: (...args) => window.Swal.fire(...args),
      success(title, text = "") {
        return window.Swal.fire({ icon: "success", title, text });
      },
      error(title, text = "") {
        return window.Swal.fire({ icon: "error", title, text });
      },
      warning(title, text = "") {
        return window.Swal.fire({ icon: "warning", title, text });
      },
      confirmDelete(html, title = "¿Eliminar registro?") {
        return window.Swal.fire({
          title,
          html,
          icon: "warning",
          showCancelButton: true,
          confirmButtonText: "Sí, eliminar",
          cancelButtonText: "Cancelar",
        });
      },
      confirmEdit(html, title = "¿Guardar cambios?") {
        return window.Swal.fire({
          title,
          html,
          icon: "question",
          showCancelButton: true,
          confirmButtonText: "Guardar cambios",
          cancelButtonText: "Cancelar",
        });
      },
      confirmCreate(html, title = "¿Guardar registro?") {
        return window.Swal.fire({
          title,
          html,
          icon: "question",
          showCancelButton: true,
          confirmButtonText: "Guardar",
          cancelButtonText: "Cancelar",
        });
      },
    };

    window.Swal.__mkThemePatched = true;
  }

  function initWhenReady() {
    if (typeof window.Swal !== "undefined") {
      patchSwal();
      return;
    }

    let tries = 0;
    const timer = setInterval(function () {
      tries += 1;
      if (typeof window.Swal !== "undefined") {
        clearInterval(timer);
        patchSwal();
      } else if (tries > 40) {
        clearInterval(timer);
      }
    }, 250);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initWhenReady);
  } else {
    initWhenReady();
  }
})();
