(() => {
  "use strict";

  const SELECTOR = "select.form-select:not(.no-tomselect)";

  function isSelectElement(el) {
    return el instanceof HTMLSelectElement;
  }

  function hasEmptyOption(select) {
    return Array.from(select.options).some((opt) => opt.value === "");
  }

  function getPlaceholder(select) {
    const custom = (select.getAttribute("placeholder") || "").trim();
    if (custom) return custom;

    const emptyOpt = Array.from(select.options).find((opt) => opt.value === "");
    if (!emptyOpt) return "";

    return (emptyOpt.textContent || "").trim();
  }

  function syncValidationState(select) {
    if (!select?.tomselect) return;

    const wrapper = select.tomselect.wrapper;
    if (!wrapper) return;

    wrapper.classList.toggle("is-invalid", select.classList.contains("is-invalid"));
    wrapper.classList.toggle("is-valid", select.classList.contains("is-valid"));
  }

  function syncDisabledState(select) {
    if (!select?.tomselect) return;

    if (select.disabled) {
      select.tomselect.disable();
    } else {
      select.tomselect.enable();
    }
  }

  function bindStateObserver(select) {
    if (!isSelectElement(select) || select._tomStateObserverBound) return;

    const observer = new MutationObserver(() => {
      syncValidationState(select);
      syncDisabledState(select);
    });

    observer.observe(select, {
      attributes: true,
      attributeFilter: ["class", "disabled"],
    });

    select._tomStateObserverBound = true;
    select._tomStateObserver = observer;
  }

  function initTomSelect(select) {
    if (!isSelectElement(select)) return;
    if (!select.matches(SELECTOR)) return;
    if (select.tomselect) return;
    if (typeof TomSelect === "undefined") return;

    const placeholder = getPlaceholder(select);
    const allowEmpty = hasEmptyOption(select);

    new TomSelect(select, {
      create: false,
      allowEmptyOption: allowEmpty,
      placeholder: placeholder || undefined,
      hidePlaceholder: false,
      closeAfterSelect: !select.multiple,
      plugins: select.multiple ? ["remove_button"] : [],
    });

    bindStateObserver(select);
    syncValidationState(select);
    syncDisabledState(select);
  }

  function initAllTomSelect(root = document) {
    if (!root) return;

    if (isSelectElement(root) && root.matches(SELECTOR)) {
      initTomSelect(root);
    }

    root.querySelectorAll?.(SELECTOR).forEach(initTomSelect);
  }

  function observeNewSelects() {
    if (!document.body) return;

    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (!(node instanceof Element)) return;
          initAllTomSelect(node);
        });
      });
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    initAllTomSelect(document);
    observeNewSelects();
  });

  window.initAllTomSelect = initAllTomSelect;
})();