// ---------------------------
// Utils
// ---------------------------
function esAjaxRequestHeaders() {
  return { "X-Requested-With": "XMLHttpRequest" };
}
function toNum(v) {
  const n = parseFloat(String(v).replace(",", "."));
  return isNaN(n) ? 0 : n;
}
function money(n) {
  return (Math.round(n * 100) / 100).toFixed(2);
}

// ============================================================
// 1) INIT CREAR VENTA (REUTILIZABLE: página y modal)
// ============================================================
function initCrearVenta(scope = document) {
  // Buscar el FORM (si no existe, salir)
  const form =
    scope.querySelector("#formCrearVenta") || scope.querySelector("form");
  if (!form) return;

  // Evitar duplicar listeners si abres el modal varias veces
  if (form.dataset.initCrearVenta === "1") return;
  form.dataset.initCrearVenta = "1";

  // Elementos
  const btnAgregarItem = form.querySelector("#btnAgregarItem");
  const btnGuardarVenta = form.querySelector("#btnGuardarVenta");
  const tipoProducto = form.querySelector("#tipo_producto");
  const tipoServicio = form.querySelector("#tipo_servicio");
  const selectCliente = form.querySelector("#id_cliente");
  const selectProducto = form.querySelector("#id_producto");
  const selectServicio = form.querySelector("#id_servicio");
  const selectPersonal = form.querySelector("#id_personal");

  const inputCantidad = form.querySelector("#id_cantidad");
  const inputPrecio = form.querySelector("#id_precio_unitario");
  const inputSubtotal = form.querySelector("#id_subtotal");

  const grupoProducto = form.querySelector("#grupoProducto");
  const grupoServicio = form.querySelector("#grupoServicio");
  const grupoPersonal = form.querySelector("#grupoPersonal");
  const grupoCantidad = form.querySelector("#grupoCantidad");

  const stockInfo = form.querySelector("#stockInfo");
  const tablaItemsBody = form.querySelector("#tablaItems tbody");
  const totalVenta = form.querySelector("#totalVenta");
  const itemsInput = form.querySelector("#itemsInput");
  const errorCantidad = form.querySelector("#cantidadError");

  // Si faltan piezas críticas, salir sin romper
  const tieneModuloCrearVenta =
    !!btnAgregarItem &&
    !!btnGuardarVenta &&
    !!tipoProducto &&
    !!tipoServicio &&
    !!selectCliente &&
    !!itemsInput &&
    !!inputCantidad &&
    !!inputPrecio &&
    !!inputSubtotal &&
    !!tablaItemsBody;

  if (!tieneModuloCrearVenta) return;

  // Estado
  let stockActual = 0;
  let items = [];

  // Inicializar input hidden
  itemsInput.value = "[]";

  // ---------------------------
  // Helpers internos
  // ---------------------------
  function syncInput() {
    itemsInput.value = JSON.stringify(items);
  }

  function renderTabla() {
    tablaItemsBody.innerHTML = "";
    let total = 0;

    items.forEach((item, i) => {
      total += item.subtotal;

      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${item.nombre}</td>
        <td class="text-end">$${money(item.precio)}</td>
        <td class="text-center">${item.cantidad}</td>
        <td class="text-end">$${money(item.subtotal)}</td>
        <td class="text-center">
          <button type="button" class="btn btn-sm btn-danger" data-index="${i}">✖</button>
        </td>
      `;
      tablaItemsBody.appendChild(tr);
    });

    if (totalVenta) totalVenta.textContent = money(total);
  }

  function actualizarBotones() {
    const tieneProducto = tipoProducto.checked;
    const tieneServicio = tipoServicio.checked;

    let puedeAgregar = false;

    if (tieneProducto) {
      const selecciono = selectProducto && selectProducto.selectedIndex > 0;
      const tieneCantidad = parseInt(inputCantidad.value || 0) > 0;
      const tienePrecio = toNum(inputPrecio.value) > 0;
      puedeAgregar = selecciono && tieneCantidad && tienePrecio;
    }

    if (tieneServicio) {
      const selecciono = selectServicio && selectServicio.selectedIndex > 0;
      const personalSel = selectPersonal && selectPersonal.selectedIndex > 0;
      const tienePrecio = toNum(inputPrecio.value) > 0;
      puedeAgregar = selecciono && personalSel && tienePrecio;
    }

    btnAgregarItem.disabled = !puedeAgregar;
    btnGuardarVenta.disabled = !(selectCliente.value && items.length > 0);
  }

  function limpiar() {
    if (selectProducto) selectProducto.value = "";
    if (selectServicio) selectServicio.value = "";
    if (selectPersonal) selectPersonal.value = "";

    inputPrecio.value = "";
    inputCantidad.value = "";
    inputSubtotal.value = "";

    if (stockInfo) stockInfo.classList.add("d-none");

    actualizarBotones();
  }

  function validarCantidad() {
    const cantidadStr = String(inputCantidad.value || "").trim();

    //  Si está vacío (todavía no han escrito), NO mostrar error
    if (cantidadStr === "") {
      if (errorCantidad) errorCantidad.classList.add("d-none");
      inputSubtotal.value = "";
      actualizarBotones();
      return;
    }

    const cantidad = parseInt(cantidadStr, 10);
    const precio = toNum(inputPrecio.value);

    //  Si no es número válido, tampoco mostramos error agresivo
    if (isNaN(cantidad) || cantidad <= 0) {
      if (errorCantidad) errorCantidad.classList.add("d-none");
      inputSubtotal.value = "";
      actualizarBotones();
      return;
    }

    //  Si se pasa del stock, ahí sí mostramos el error
    if (cantidad > stockActual) {
      if (errorCantidad) errorCantidad.classList.remove("d-none");
      btnAgregarItem.disabled = true;
      inputSubtotal.value = "";
      return;
    }

    // Caso correcto
    if (errorCantidad) errorCantidad.classList.add("d-none");
    inputSubtotal.value = money(precio * cantidad);
    actualizarBotones();
  }
  // ---------------------------
  // Eventos: seleccionar tipo
  // ---------------------------
  tipoProducto.addEventListener("change", () => {
    if (grupoProducto) grupoProducto.classList.remove("d-none");
    if (grupoCantidad) grupoCantidad.classList.remove("d-none");
    if (grupoServicio) grupoServicio.classList.add("d-none");
    if (grupoPersonal) grupoPersonal.classList.add("d-none");

    if (selectProducto) selectProducto.disabled = false;
    if (selectServicio) selectServicio.disabled = true;
    if (selectPersonal) selectPersonal.disabled = true;

    if (selectServicio) selectServicio.value = "";
    if (selectPersonal) selectPersonal.value = "";

    inputPrecio.value = "";
    inputCantidad.value = "";
    inputSubtotal.value = "";
    if (stockInfo) stockInfo.classList.add("d-none");

    actualizarBotones();
    actualizarTextoBoton();
  });

  tipoServicio.addEventListener("change", () => {
    if (grupoProducto) grupoProducto.classList.add("d-none");
    if (grupoCantidad) grupoCantidad.classList.add("d-none");
    if (grupoServicio) grupoServicio.classList.remove("d-none");
    if (grupoPersonal) grupoPersonal.classList.remove("d-none");

    if (selectProducto) selectProducto.disabled = true;
    if (selectServicio) selectServicio.disabled = false;
    if (selectPersonal) selectPersonal.disabled = false;

    if (selectProducto) selectProducto.value = "";

    inputPrecio.value = "";
    inputCantidad.value = "1";
    inputSubtotal.value = "";
    if (stockInfo) stockInfo.classList.add("d-none");

    actualizarBotones();
    actualizarTextoBoton();
  });

  // ---------------------------
  // Producto seleccionado
  // ---------------------------
  if (selectProducto) {
    selectProducto.addEventListener("change", () => {
      const opt = selectProducto.options[selectProducto.selectedIndex];
      if (selectProducto.selectedIndex === 0) return;

      stockActual = parseInt(opt.dataset.stock) || 0;
      const precio = toNum(opt.dataset.precio);

      inputPrecio.value = money(precio);
      inputCantidad.value = "";
      inputSubtotal.value = "";

      if (stockInfo) {
        stockInfo.classList.remove("d-none");
        if (stockActual > 0) {
          stockInfo.textContent = ` Disponible: ${stockActual} unidades`;
          stockInfo.className = "text-success small";
        } else {
          stockInfo.textContent = " Sin stock disponible";
          stockInfo.className = "text-danger small";
        }
      }

      validarCantidad();
      actualizarBotones();
    });
  }

  // ---------------------------
  // Servicio seleccionado
  // ---------------------------
  if (selectServicio) {
    selectServicio.addEventListener("change", () => {
      const opt = selectServicio.options[selectServicio.selectedIndex];
      if (selectServicio.selectedIndex === 0) return;

      const precio = toNum(opt.dataset.precio);
      inputPrecio.value = money(precio);
      inputSubtotal.value = money(precio);
      actualizarBotones();
    });
  }

  if (selectPersonal)
    selectPersonal.addEventListener("change", actualizarBotones);
  if (selectCliente)
    selectCliente.addEventListener("change", actualizarBotones);
  if (inputCantidad) inputCantidad.addEventListener("input", validarCantidad);

  // ---------------------------
  // Agregar item
  // ---------------------------
  btnAgregarItem.addEventListener("click", (e) => {
    e.preventDefault();

    if (tipoProducto.checked) {
      if (!selectProducto || selectProducto.selectedIndex === 0) {
        Swal?.fire?.({
          icon: "warning",
          title: "Debes seleccionar un producto",
        });
        return;
      }

      const codigoProducto = parseInt(selectProducto.value);
      if (isNaN(codigoProducto)) return;

      const nombreProducto =
        selectProducto.options[selectProducto.selectedIndex].textContent.trim();
      const cantidad = parseInt(inputCantidad.value || 0);
      const precio = toNum(inputPrecio.value);
      const subtotal = toNum(inputSubtotal.value);

      if (!cantidad || cantidad <= 0 || cantidad > stockActual) {
        Swal?.fire?.({
          icon: "warning",
          title: "Cantidad inválida o superior al stock disponible",
        });
        return;
      }

      items.push({
        tipo: "producto",
        id: codigoProducto,
        nombre: nombreProducto,
        precio,
        cantidad,
        subtotal,
      });
    }

    if (tipoServicio.checked) {
      if (!selectServicio || selectServicio.selectedIndex === 0) {
        Swal?.fire?.({
          icon: "warning",
          title: "Debes seleccionar un servicio",
        });
        return;
      }
      if (!selectPersonal || selectPersonal.selectedIndex === 0) {
        Swal?.fire?.({
          icon: "warning",
          title: "Selecciona la persona que realizó el servicio",
        });
        return;
      }

      const idx = selectServicio.selectedIndex;
      const precio = toNum(inputPrecio.value);

      items.push({
        tipo: "servicio",
        id_servicio: selectServicio.options[idx].value,
        id_personal: selectPersonal.options[selectPersonal.selectedIndex].value,
        nombre: selectServicio.options[idx].textContent.trim(),
        precio,
        cantidad: 1,
        subtotal: precio,
      });
    }

    renderTabla();
    syncInput();
    limpiar();
  });

  // ---------------------------
  // Eliminar item (delegación)
  // ---------------------------
  tablaItemsBody.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-index]");
    if (!btn) return;

    const i = parseInt(btn.dataset.index);
    if (isNaN(i)) return;

    items.splice(i, 1);
    renderTabla();
    syncInput();
    actualizarBotones();
  });

  // Init botones
  btnAgregarItem.disabled = true;
  btnGuardarVenta.disabled = true;
  actualizarTextoBoton();
  function actualizarTextoBoton() {
    if (!btnAgregarItem) return;

    if (tipoProducto.checked) {
      btnAgregarItem.innerHTML = "➕ Agregar producto";
    } else if (tipoServicio.checked) {
      btnAgregarItem.innerHTML = "➕ Agregar servicio";
    } else {
      btnAgregarItem.innerHTML = "➕ Agregar producto / servicio";
    }
  }

  if (selectProducto && !selectProducto.tomselect) {
    new TomSelect(selectProducto, {
      create: false,
      dropdownParent: "body",
      sortField: {
        field: "text",
        direction: "asc",
      },
    });
  }

  if (selectServicio && !selectServicio.tomselect) {
    new TomSelect(selectServicio, {
      create: false,
      dropdownParent: "body",
      sortField: {
        field: "text",
        direction: "asc",
      },
    });
  }
  // ================================
  // Tom Select: quitar azul nativo
  // ================================
  function applyTomSelect(sel) {
    if (!sel) return;
    if (sel.tomselect) return; // ya aplicado
    new TomSelect(sel, {
      create: false,
      allowEmptyOption: true,
      dropdownParent: "body",
      sortField: { field: "text", direction: "asc" },
    });
  }

  applyTomSelect(selectCliente);
  applyTomSelect(selectProducto);
  applyTomSelect(selectServicio);
  applyTomSelect(selectPersonal);
}

// Init al cargar cualquier página
document.addEventListener("DOMContentLoaded", () => {
  initCrearVenta(document);
});

// ============================================================
// 2) MODAL NUEVA VENTA (ABRIR + GUARDAR POR AJAX)
// ============================================================
document.addEventListener("click", async function (e) {
  const btnNueva = e.target.closest("#btnNuevaVenta");
  if (!btnNueva) return;

  const url = btnNueva.dataset.url;

  const modalEl = document.getElementById("modalNuevaVenta");
  const contenido = document.getElementById("contenidoNuevaVenta");

  if (!modalEl || !contenido) {
    console.error(
      "No existe #modalNuevaVenta o #contenidoNuevaVenta en el HTML",
    );
    return;
  }

  const modal = new bootstrap.Modal(modalEl);

  contenido.innerHTML = `<div class="text-center text-muted py-4">Cargando…</div>`;

  try {
    const res = await fetch(url, { headers: esAjaxRequestHeaders() });
    if (!res.ok) throw new Error("HTTP " + res.status);

    const data = await res.json();
    contenido.innerHTML = data.html || "";

    // ✅ activar lógica del formulario dentro del modal
    initCrearVenta(modalEl);

    modal.show();
  } catch (err) {
    console.error("Error cargando Nueva venta:", err);
    contenido.innerHTML = `<div class="alert alert-danger mb-0">No se pudo cargar: ${err.message}</div>`;
  }
});

// Submit del form crear venta dentro del modal (AJAX)
document.addEventListener("submit", async function (e) {
  const form = e.target;
  if (!form.matches("#formCrearVenta")) return;

  // Solo si está dentro del modal
  const modalEl = form.closest("#modalNuevaVenta");
  if (!modalEl) return;

  e.preventDefault();

  // El form NO tiene action en tu parcial, entonces usamos el data-url del botón
  const btnNueva = document.getElementById("btnNuevaVenta");
  const url = btnNueva ? btnNueva.dataset.url : window.location.href;

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: esAjaxRequestHeaders(),
      body: new FormData(form),
    });

    if (!res.ok) throw new Error("HTTP " + res.status);

    const data = await res.json();

    if (data.success === true) {
      // cerrar modal
      const modal = bootstrap.Modal.getInstance(modalEl);
      if (modal) modal.hide();

      await Swal.fire({
        icon: "success",
        title: "Venta registrada",
        timer: 1400,
        showConfirmButton: false,
      });

      location.reload();
    } else {
      // Re-render con errores
      const contenido = document.getElementById("contenidoNuevaVenta");
      contenido.innerHTML =
        data.html ||
        "<div class='alert alert-danger'>Error en formulario.</div>";

      // volver a enganchar listeners
      initCrearVenta(modalEl);
    }
  } catch (err) {
    Swal?.fire?.({
      icon: "error",
      title: "Error al guardar",
      text: err.message,
    });
  }
});

// ============================================================
// 3) MODALES LISTA: DETALLE (JSON) + EDITAR (HTML)
// ============================================================
function applyTomSelectIn(scope) {
  if (!scope || typeof TomSelect === "undefined") return;

  const selects = scope.querySelectorAll(
    "select.js-prod-select, select.js-serv-servicio, select[name^='serv_personal_']",
  );

  selects.forEach((sel) => {
    if (!sel || sel.tomselect) return;

    new TomSelect(sel, {
      create: false,
      allowEmptyOption: true,
      dropdownParent: "body",
      sortField: { field: "$order", direction: "asc" },
    });
  });
}

function hydrateEditarModalPrices(scope) {
  if (!scope) return;

  // Productos: precio siempre desde option[data-precio]
  scope.querySelectorAll("select.js-prod-select").forEach((sel) => {
    const detalleId = sel.dataset.detalle;
    const opt = sel.options?.[sel.selectedIndex];
    if (!detalleId || !opt) return;

    const precio = parseFloat(opt.dataset.precio) || 0;

    const precioInput = scope.querySelector(
      `.js-prod-precio[data-detalle="${detalleId}"]`,
    );
    const cantInput = scope.querySelector(
      `.js-prod-cant[data-detalle="${detalleId}"]`,
    );
    const subInput = scope.querySelector(
      `.js-prod-subtotal[data-detalle="${detalleId}"]`,
    );

    if (precioInput) precioInput.value = precio.toFixed(2);
    const cant = cantInput ? parseFloat(cantInput.value) || 0 : 0;
    if (subInput) subInput.value = (cant * precio).toFixed(2);
  });

  // Servicios: precio siempre desde option[data-precio]
  scope.querySelectorAll("select.js-serv-servicio").forEach((sel) => {
    const detalleId = sel.dataset.detalle;
    const opt = sel.options?.[sel.selectedIndex];
    if (!detalleId || !opt) return;

    const precio = parseFloat(opt.dataset.precio) || 0;
    const precioInput = scope.querySelector(
      `.js-serv-precio[data-detalle="${detalleId}"]`,
    );
    const cantInput = scope.querySelector(
      `.js-serv-cant[data-detalle="${detalleId}"]`,
    );
    const subInput = scope.querySelector(
      `.js-serv-subtotal[data-detalle="${detalleId}"]`,
    );

    if (precioInput) precioInput.value = precio.toFixed(2);
    const cant = cantInput ? parseFloat(cantInput.value) || 0 : 0;
    if (subInput) subInput.value = (cant * precio).toFixed(2);
  });

  recalcTotalEditar();
}

document.addEventListener("click", async function (e) {
  // ---- DETALLE ----
  const btnDetalle = e.target.closest(".btn-ver-detalle");
  if (btnDetalle) {
    const url = btnDetalle.dataset.url;
    const cont = document.getElementById("contenidoDetalleVenta");
    if (!cont) return;

    cont.innerHTML = `<div class="text-center text-muted py-4">Cargando...</div>`;

    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error("HTTP " + res.status);

      const v = await res.json();

      const filas = (v.detalles || [])
        .map(
          (d) => `
        <tr>
          <td>${d.tipo || "-"}</td>
          <td>${d.nombre || "-"}</td>
          <td class="text-center">${d.cantidad || 0}</td>
          <td class="text-end">$${d.precio_unitario || "0.00"}</td>
          <td class="text-end">$${d.subtotal || "0.00"}</td>
        </tr>
      `,
        )
        .join("");

      cont.innerHTML = `
        <div class="row g-2 mb-3">
          <div class="col-md-6"><strong>Código venta:</strong> ${v.codigo_venta || "-"}</div>
          <div class="col-md-6"><strong>Fecha:</strong> ${v.fecha || "-"}</div>
          <div class="col-md-6"><strong>Cliente:</strong> ${v.cliente || "-"}</div>
          <div class="col-md-6"><strong>Estado:</strong> ${v.estado || "-"}</div>
        </div>

        <div class="table-responsive">
          <table class="table table-sm align-middle">
            <thead>
              <tr>
                <th>Tipo</th>
                <th>Nombre</th>
                <th class="text-center">Cantidad</th>
                <th class="text-end">Precio</th>
                <th class="text-end">Subtotal</th>
              </tr>
            </thead>
            <tbody>
              ${filas || `<tr><td colspan="5" class="text-center text-muted">Sin detalles</td></tr>`}
            </tbody>
          </table>
        </div>

        <div class="text-end fw-bold mt-2">
          Total: $${v.total || "0.00"}
        </div>
      `;
    } catch (err) {
      cont.innerHTML = `<div class="alert alert-danger mb-0">No se pudo cargar el detalle: ${err.message}</div>`;
    }

    return;
  }

  // ---- EDITAR ----
  const btnEditar = e.target.closest(".btn-editar");
  if (btnEditar) {
    const url = btnEditar.dataset.url;
    const cont = document.getElementById("contenidoEditarVenta");
    const modalEl = document.getElementById("modalEditarVenta");
    if (!cont || !modalEl) return;

    cont.innerHTML = '<div class="text-center text-muted py-4">Cargando...</div>';

    try {
      const res = await fetch(url, { headers: esAjaxRequestHeaders() });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();

      cont.innerHTML = data.html || "";
      applyTomSelectIn(cont);
      hydrateEditarModalPrices(cont);
      const modal = new bootstrap.Modal(modalEl);
      modal.show();
    } catch (err) {
      cont.innerHTML = '<div class="alert alert-danger mb-0">No se pudo cargar: ' + err.message + '</div>';
    }
  }
});

function precargarItemsEdicion(form, items) {
  if (!items || !items.length) return;
  var tablaBody = form.querySelector("#tablaItems tbody");
  var itemsInput = form.querySelector("#itemsInput");
  var totalEl = form.querySelector("#totalVenta");
  if (!tablaBody || !itemsInput) return;

  // Inyectar ítems directamente en el input hidden y renderizar la tabla
  itemsInput.value = JSON.stringify(items);

  var total = 0;
  tablaBody.innerHTML = "";
  items.forEach(function(item, i) {
    total += item.subtotal || 0;
    var tr = document.createElement("tr");
    tr.innerHTML = '<td>' + item.nombre + '</td>'
      + '<td class="text-end">$' + (item.precio||0).toFixed(2) + '</td>'
      + '<td class="text-center">' + (item.cantidad||1) + '</td>'
      + '<td class="text-end">$' + (item.subtotal||0).toFixed(2) + '</td>'
      + '<td class="text-center"><button type="button" class="btn btn-sm btn-danger" data-index="' + i + '">✖</button></td>';
    tablaBody.appendChild(tr);
  });
  if (totalEl) totalEl.textContent = total.toFixed(2);
}

// Submit EDITAR
document.addEventListener("submit", async function (e) {
  const form = e.target;
  if (!form.matches("#formEditarVenta")) return;

  e.preventDefault();

  const url = form.action;
  const cont = document.getElementById("contenidoEditarVenta");

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: esAjaxRequestHeaders(),
      body: new FormData(form),
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const data = await res.json();

    if (data.ok) {
      const modalEl = document.getElementById("modalEditarVenta");
      const modal = bootstrap.Modal.getInstance(modalEl);
      if (modal) modal.hide();
      await Swal.fire({
        icon: "success",
        title: "Venta actualizada",
        timer: 1400,
        showConfirmButton: false,
      });
      location.reload();
    } else {
      Swal.fire({ icon: "error", title: "Error", text: data.error || "No se pudo guardar." });
    }
  } catch (err) {
    Swal.fire({ icon: "error", title: "Error", text: err.message });
  }
});
// Recalcular subtotal productos (editar)
document.addEventListener("input", function(e) {
  const cant = e.target.closest(".js-prod-cant");
  const precio = e.target.closest(".js-prod-precio");
  if (!cant && !precio) return;

  const id = (cant || precio).dataset.detalle;
  const c = document.querySelector('.js-prod-cant[data-detalle="' + id + '"]');
  const p = document.querySelector('.js-prod-precio[data-detalle="' + id + '"]');
  const s = document.querySelector('.js-prod-subtotal[data-detalle="' + id + '"]');

  if (cant) {
    var stock = parseInt(cant.dataset.stock || "0");
    var val = parseInt(cant.value) || 0;
    var errEl = document.querySelector('.err-stock-' + id);

    // No permitir escribir más de lo disponible (1..stock)
    if (stock <= 0) {
      cant.value = 0;
      cant.classList.add("is-invalid");
      if (errEl) {
        errEl.textContent = "Sin stock";
        errEl.classList.remove("d-none");
      }
    } else {
      if (val < 1) val = 1;
      if (val > stock) val = stock;
      if (String(cant.value) !== String(val)) cant.value = val;

      cant.classList.remove("is-invalid");
      if (errEl) errEl.classList.add("d-none");
    }
  }

  if (c && p && s) {
    var subtotal = (parseFloat(c.value) || 0) * (parseFloat(p.value) || 0);
    s.value = subtotal.toFixed(2);
    recalcTotalEditar();
  }
});

// Cambiar producto en editar: actualizar precio, stock y subtotal
document.addEventListener("change", function(e) {
  const sel = e.target.closest(".js-prod-select");
  if (!sel) return;
  var id = sel.dataset.detalle;
  var opt = sel.options[sel.selectedIndex];
  var nuevoPrecio = parseFloat(opt.dataset.precio) || 0;
  var nuevoStock = parseInt(opt.dataset.stock) || 0;

  var precioInput = document.querySelector('.js-prod-precio[data-detalle="' + id + '"]');
  var cantInput   = document.querySelector('.js-prod-cant[data-detalle="' + id + '"]');
  var subInput    = document.querySelector('.js-prod-subtotal[data-detalle="' + id + '"]');
  var errEl       = document.querySelector('.err-stock-' + id);

  if (precioInput) precioInput.value = nuevoPrecio.toFixed(2);
  if (cantInput) {
    cantInput.dataset.stock = nuevoStock;
    cantInput.max = nuevoStock;
    var cant = parseInt(cantInput.value) || 1;
    if (cant > nuevoStock) {
      cantInput.value = nuevoStock;
      cant = nuevoStock;
    }
    cantInput.classList.remove("is-invalid");
    if (errEl) errEl.classList.add("d-none");
    if (subInput) subInput.value = (cant * nuevoPrecio).toFixed(2);
  }

  // Actualizar badge de stock en la tabla (editar)
  var badge = document.querySelector('.js-prod-stock-badge[data-detalle="' + id + '"]');
  if (badge) {
    badge.textContent = String(nuevoStock);
    if (nuevoStock < 5) {
      badge.style.background = "rgba(180,35,24,0.1)";
      badge.style.color = "#b42318";
    } else {
      badge.style.background = "rgba(22,101,52,0.1)";
      badge.style.color = "#166534";
    }
  }

  recalcTotalEditar();
});

// Recalcular subtotal servicios (editar)
document.addEventListener("change", function(e) {
  const sel = e.target.closest(".js-serv-servicio");
  if (!sel) return;
  const id = sel.dataset.detalle;
  const opt = sel.options[sel.selectedIndex];
  const precio = parseFloat(opt.dataset.precio) || 0;
  const precioInput = document.querySelector('.js-serv-precio[data-detalle="' + id + '"]');
  const cantInput = document.querySelector('.js-serv-cant[data-detalle="' + id + '"]');
  const subInput = document.querySelector('.js-serv-subtotal[data-detalle="' + id + '"]');
  if (precioInput) precioInput.value = precio.toFixed(2);
  if (cantInput && subInput) {
    subInput.value = ((parseFloat(cantInput.value) || 1) * precio).toFixed(2);
    recalcTotalEditar();
  }
});

document.addEventListener("input", function(e) {
  const cant = e.target.closest(".js-serv-cant");
  if (!cant) return;
  const id = cant.dataset.detalle;
  const precioInput = document.querySelector('.js-serv-precio[data-detalle="' + id + '"]');
  const subInput = document.querySelector('.js-serv-subtotal[data-detalle="' + id + '"]');
  if (precioInput && subInput) {
    subInput.value = ((parseFloat(cant.value) || 0) * (parseFloat(precioInput.value) || 0)).toFixed(2);
    recalcTotalEditar();
  }
});

function recalcTotalEditar() {
  var total = 0;
  document.querySelectorAll(".js-prod-subtotal, .js-serv-subtotal").forEach(function(el) {
    total += parseFloat(el.value) || 0;
  });
  var totalEl = document.getElementById("totalEditar");
  if (totalEl) totalEl.textContent = "$ " + total.toLocaleString("es-CO", {minimumFractionDigits:2});
}

// Eliminar función precargarItemsEdicion si existe (ya no se usa)


// ============================================================
// 4) CONFIRMAR CAMBIO DE ESTADO (SWITCH) - CAPTURA
// ============================================================
document.addEventListener(
  "change",
  function (e) {
    const chk = e.target;
    if (!chk.classList.contains("toggle-estado")) return;

    if (typeof Swal === "undefined") {
      console.error(
        "❌ SweetAlert2 no está cargado. Revisa el orden de scripts.",
      );
      return;
    }

    e.stopImmediatePropagation();

    const form = chk.closest("form");
    if (!form) return;

    const estadoAntes = chk.getAttribute("data-estado"); // activa/anulada
    const vaAActivar = estadoAntes === "anulada";

    const titulo = vaAActivar
      ? "¿Seguro de activar nuevamente la venta?"
      : "¿Seguro de anular la venta?";

    const texto = vaAActivar
      ? "La venta quedará ACTIVA nuevamente."
      : "La venta quedará ANULADA.";

    const confirmText = vaAActivar ? "Sí, activar" : "Sí, anular";

    Swal.fire({
      title: titulo,
      text: texto,
      icon: "warning",
      showCancelButton: true,
      confirmButtonText: confirmText,
      cancelButtonText: "Cancelar",
      reverseButtons: true,
    }).then((r) => {
      if (r.isConfirmed) {
        form.submit();
      } else {
        chk.checked = !chk.checked;
      }
    });
  },
  true,
);
let chartPreviewPrincipal = null;

function destruirChartsReporte() {
  if (chartPreviewPrincipal) {
    chartPreviewPrincipal.destroy();
    chartPreviewPrincipal = null;
  }
}

function normalizarTipoGrafica(tipo) {
  if (tipo === "funnel") return "bar";
  return tipo || "bar";
}

function construirDatasetFunnel(data) {
  const max = Math.max(...data, 0);
  if (max <= 0) return data;

  return data.map((valor, index) => {
    const factor = 1 - (index * 0.12);
    return Math.max(valor * factor, 0);
  });
}

function renderizarGraficaReporte(canvasId, datasets, labelsUnion, tipoGrafica) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;

  const tipoFinal = normalizarTipoGrafica(tipoGrafica);
  const colores = [
    { border: "#8d604a", bg: "rgba(141,96,74,0.25)" },
    { border: "#4a7c8d", bg: "rgba(74,124,141,0.25)" },
  ];

  const chartDatasets = datasets.map((ds, i) => {
    let dataFinal = tipoGrafica === "funnel" ? construirDatasetFunnel(ds.data) : [...ds.data];
    return {
      label: ds.label,
      data: dataFinal,
      borderColor: colores[i % colores.length].border,
      backgroundColor: tipoFinal === "line" ? colores[i % colores.length].bg : colores[i % colores.length].border,
      borderWidth: tipoFinal === "line" ? 2 : 1,
      tension: 0.3,
      fill: false,
      pointRadius: tipoFinal === "line" ? 4 : 0,
    };
  });

  return new Chart(canvas, {
    type: tipoFinal,
    data: {
      labels: labelsUnion,
      datasets: chartDatasets,
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: true },
        tooltip: { mode: "index", intersect: false },
      },
      scales: {
        x: { ticks: { maxRotation: 45 } },
        y: { beginAtZero: true },
      },
    },
  });
}
// ============================================================
// 5) REPORTE VENTAS: COMPARATIVO + VISTA PREVIA + EXPORTAR
// ============================================================
document.addEventListener("change", function (e) {
  const checkComparativo = e.target.closest("#checkComparativoVentas");
  if (!checkComparativo) return;

  const bloque = document.getElementById("bloqueComparativoVentas");
  if (!bloque) return;

  const inicioComp = bloque.querySelector('input[name="fecha_inicio_comp"]');
  const finComp = bloque.querySelector('input[name="fecha_fin_comp"]');
  const form = document.getElementById("formReporteVentas");
  const checkGrafica = form ? form.querySelector('input[name="incluir_grafica"]') : null;
  const labelGrafica = checkGrafica ? checkGrafica.closest("label") : null;
  const bloqueTipo = document.getElementById("bloqueTipoGraficaVentas");

  if (checkComparativo.checked) {
    bloque.classList.remove("d-none");
    if (inicioComp) inicioComp.required = true;
    if (finComp) finComp.required = true;

    // Gráfica solo disponible en modo comparativo
    if (checkGrafica) checkGrafica.disabled = false;
    if (labelGrafica) {
      labelGrafica.style.opacity = "";
      labelGrafica.style.pointerEvents = "";
    }
  } else {
    bloque.classList.add("d-none");
    if (inicioComp) {
      inicioComp.required = false;
      inicioComp.value = "";
    }
    if (finComp) {
      finComp.required = false;
      finComp.value = "";
    }

    // Desactivar gráfica si no hay comparativo
    if (checkGrafica) {
      checkGrafica.checked = false;
      checkGrafica.disabled = true;
    }
    if (bloqueTipo) bloqueTipo.classList.add("d-none");
    if (labelGrafica) {
      labelGrafica.style.opacity = "0.55";
      labelGrafica.style.pointerEvents = "none";
    }
  }
});

// Estado inicial del checkbox de gráfica: solo habilitado si comparativo está activo.
document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("formReporteVentas");
  if (!form) return;

  const checkComparativo = document.getElementById("checkComparativoVentas");
  const comparativoActivo = !!(checkComparativo && checkComparativo.checked);

  const checkGrafica = form.querySelector('input[name="incluir_grafica"]');
  const labelGrafica = checkGrafica ? checkGrafica.closest("label") : null;
  const bloqueTipo = document.getElementById("bloqueTipoGraficaVentas");

  if (!comparativoActivo) {
    if (checkGrafica) {
      checkGrafica.checked = false;
      checkGrafica.disabled = true;
    }
    if (bloqueTipo) bloqueTipo.classList.add("d-none");
    if (labelGrafica) {
      labelGrafica.style.opacity = "0.55";
      labelGrafica.style.pointerEvents = "none";
    }
  } else {
    if (checkGrafica) checkGrafica.disabled = false;
    if (labelGrafica) {
      labelGrafica.style.opacity = "";
      labelGrafica.style.pointerEvents = "";
    }
  }
});


// ============================================================
// VALIDACION DE FECHAS — REPORTE
// ============================================================

function hoy() {
  return new Date(new Date().toDateString());
}

function parseDate(str) {
  if (!str) return null;
  var parts = str.split("-");
  return new Date(parts[0], parts[1] - 1, parts[2]);
}

function setFieldError(inputId, errId, msg) {
  var inp = document.getElementById(inputId);
  var err = document.getElementById(errId);
  if (!inp) return;
  if (msg) {
    inp.classList.add("is-invalid");
    if (err) { err.textContent = msg; }
  } else {
    inp.classList.remove("is-invalid");
    if (err) { err.textContent = ""; }
  }
}

function clearAllDateErrors() {
  ["id_fecha_inicio","id_fecha_fin","id_fecha_inicio_comp","id_fecha_fin_comp"].forEach(function(id) {
    setFieldError(id, "err_" + id.replace("id_",""), null);
  });
}

function validarFechasReporte(form) {
  clearAllDateErrors();
  var errores = [];

  var fi   = form.querySelector('[name="fecha_inicio"]').value;
  var ff   = form.querySelector('[name="fecha_fin"]').value;
  var esComparativo = form.querySelector('[name="comparativo"]') && form.querySelector('[name="comparativo"]').checked;
  var fic  = esComparativo ? form.querySelector('[name="fecha_inicio_comp"]').value : "";
  var ffc  = esComparativo ? form.querySelector('[name="fecha_fin_comp"]').value : "";

  var today = hoy();
  var dFi  = parseDate(fi);
  var dFf  = parseDate(ff);
  var dFic = parseDate(fic);
  var dFfc = parseDate(ffc);

  // ── Rango principal ────────────────────────────────────
  if (!fi) {
    setFieldError("id_fecha_inicio", "err_fecha_inicio", "La fecha inicial es obligatoria.");
    errores.push("fecha_inicio");
  }
  if (!ff) {
    setFieldError("id_fecha_fin", "err_fecha_fin", "La fecha final es obligatoria.");
    errores.push("fecha_fin");
  }

  if (dFf && dFf > today) {
    setFieldError("id_fecha_fin", "err_fecha_fin", "La fecha final no puede ser posterior a hoy.");
    errores.push("fecha_fin_futura");
  }
  if (dFi && dFi > today) {
    setFieldError("id_fecha_inicio", "err_fecha_inicio", "La fecha inicial no puede ser posterior a hoy.");
    errores.push("fecha_inicio_futura");
  }
  if (dFi && dFf && dFi > dFf) {
    setFieldError("id_fecha_inicio", "err_fecha_inicio", "La fecha inicial no puede ser posterior a la fecha final.");
    errores.push("rango_inv");
  }
  if (dFi && dFf && dFi.getTime() === dFf.getTime()) {
    setFieldError("id_fecha_fin", "err_fecha_fin", "La fecha final no puede ser igual a la fecha inicial.");
    errores.push("mismo_dia");
  }

  // ── Rango comparativo ──────────────────────────────────
  if (esComparativo) {
    if (!fic) {
      setFieldError("id_fecha_inicio_comp", "err_fecha_inicio_comp", "La fecha inicial comparativa es obligatoria.");
      errores.push("fic_vacia");
    }
    if (!ffc) {
      setFieldError("id_fecha_fin_comp", "err_fecha_fin_comp", "La fecha final comparativa es obligatoria.");
      errores.push("ffc_vacia");
    }
    if (dFfc && dFfc > today) {
      setFieldError("id_fecha_fin_comp", "err_fecha_fin_comp", "La fecha final comparativa no puede ser posterior a hoy.");
      errores.push("ffc_futura");
    }
    if (dFic && dFic > today) {
      setFieldError("id_fecha_inicio_comp", "err_fecha_inicio_comp", "La fecha inicial comparativa no puede ser posterior a hoy.");
      errores.push("fic_futura");
    }
    if (dFic && dFfc && dFic > dFfc) {
      setFieldError("id_fecha_inicio_comp", "err_fecha_inicio_comp", "La fecha inicial comparativa no puede ser posterior a la final.");
      errores.push("comp_rango_inv");
    }
    if (dFic && dFfc && dFic.getTime() === dFfc.getTime()) {
      setFieldError("id_fecha_fin_comp", "err_fecha_fin_comp", "Las fechas comparativas no pueden ser iguales.");
      errores.push("comp_mismo_dia");
    }
    // Rango comparativo no puede ser igual al principal
    if (dFi && dFf && dFic && dFfc &&
        dFi.getTime() === dFic.getTime() && dFf.getTime() === dFfc.getTime()) {
      setFieldError("id_fecha_inicio_comp", "err_fecha_inicio_comp", "El rango comparativo no puede ser idéntico al rango principal.");
      setFieldError("id_fecha_fin_comp", "err_fecha_fin_comp", "El rango comparativo no puede ser idéntico al rango principal.");
      errores.push("comp_igual_principal");
    }
  }

  return errores.length === 0;
}

// Validacion en tiempo real al cambiar cualquier fecha
document.addEventListener("change", function(e) {
  var names = ["fecha_inicio","fecha_fin","fecha_inicio_comp","fecha_fin_comp"];
  var matched = names.some(function(n) { return e.target.name === n; });
  if (!matched) return;
  var form = document.getElementById("formReporteVentas");
  if (form) validarFechasReporte(form);
});

document.addEventListener("click", async function (e) {
  const btnPreview = e.target.closest("#btnVistaPreviaReporte");
  if (!btnPreview) return;

  const form = document.getElementById("formReporteVentas");
  const cont = document.getElementById("contenidoVistaPreviaReporte");
  const modalEl = document.getElementById("modalVistaPreviaReporte");

  if (!form || !cont || !modalEl) return;

  const columnas = form.querySelectorAll('input[name="columnas"]:checked');
  if (columnas.length === 0) {
    Swal.fire({
      icon: "warning",
      title: "Selecciona al menos una columna",
    });
    return;
  }

  if (!validarFechasReporte(form)) {
    Swal.fire({
      icon: "warning",
      title: "Revisa las fechas",
      text: "Corrige los errores en las fechas antes de continuar.",
      confirmButtonColor: "#8d604a",
    });
    return;
  }

  const formData = new FormData(form);
  const params = new URLSearchParams(formData);

  const btnDescargar = document.getElementById("btnDescargarReporteVentas");

  function buildExcelUrl(paramsInstance) {
    const excelParams = new URLSearchParams(paramsInstance.toString());
    excelParams.set("formato", "excel");
    return `/ventas/reporte/exportar/?${excelParams.toString()}`;
  }

  function buildPdfFilename(paramsInstance) {
    const fi = paramsInstance.get("fecha_inicio") || "";
    const ff = paramsInstance.get("fecha_fin") || "";
    const suffix = fi && ff ? `_${fi}_${ff}` : "";
    return `reporte_ventas${suffix}.pdf`;
  }

  const loadingHTML = `
    <div class="comprobante-loading">
      <div class="spinner-border" role="status"></div>
      <p class="mt-3 mb-0">Cargando vista previa...</p>
    </div>
  `;

  async function cargarVistaPreviaReporteVentas(paramsInstance) {
    cont.innerHTML = loadingHTML;
    const modal = new bootstrap.Modal(modalEl);
    modal.show();

    const res = await fetch(`/ventas/reporte/vista-previa/?${paramsInstance.toString()}`, {
      headers: esAjaxRequestHeaders(),
    });

    if (!res.ok) throw new Error("HTTP " + res.status);

    const data = await res.json();

    destruirChartsReporte();
    cont.innerHTML = data.html || "<div class='alert alert-danger'>No se pudo generar la vista previa.</div>";

    // Renderizar gráfica (si la pidió el usuario)
    await new Promise((resolve) => requestAnimationFrame(resolve));
    if (data.incluir_grafica && data.comparativo) {
      const pLabels = data.grafica_principal_labels || [];
      const pData   = data.grafica_principal_data   || [];
      const cLabels = data.grafica_comp_labels || [];
      const cData   = data.grafica_comp_data   || [];

      function alinear(labels, vals, union) {
        return union.map((lbl) => {
          const i = labels.indexOf(lbl);
          return i >= 0 ? vals[i] : null;
        });
      }

      function parseDMY(label) {
        if (!label || typeof label !== "string") return NaN;
        const parts = label.split("/");
        if (parts.length !== 3) return NaN;
        const d = parseInt(parts[0], 10);
        const m = parseInt(parts[1], 10);
        const y = parseInt(parts[2], 10);
        if (!d || !m || !y) return NaN;
        return new Date(y, m - 1, d).getTime();
      }

      const allLabels = data.comparativo
        ? [...new Set([...pLabels, ...cLabels])].sort((a, b) => {
            const ta = parseDMY(a);
            const tb = parseDMY(b);
            if (!Number.isFinite(ta) || !Number.isFinite(tb)) return String(a).localeCompare(String(b));
            return ta - tb;
          })
        : pLabels;

      const datasets = [];

      if (pLabels.length) {
        datasets.push({
          label: data.comparativo
            ? "Principal (" + (data.fecha_inicio || "") + " — " + (data.fecha_fin || "") + ")"
            : "Ventas",
          data: data.comparativo ? alinear(pLabels, pData, allLabels) : pData,
        });
      }

      if (data.comparativo && cLabels.length) {
        datasets.push({
          label: "Comparativo (" + (data.fecha_inicio_comp || "") + " — " + (data.fecha_fin_comp || "") + ")",
          data: alinear(cLabels, cData, allLabels),
        });
      }

      const canvas = document.getElementById("graficaPreviewPrincipal");
      if (canvas) {
        const tipo = (data.tipo_grafica || "bar").toLowerCase();
        chartPreviewPrincipal = renderizarGraficaReporte(
          "graficaPreviewPrincipal",
          datasets,
          allLabels,
          (tipo === "funnel" ? "bar" : tipo),
        );
      }
    }

    if (btnDescargar) {
      btnDescargar.dataset.excelUrl = buildExcelUrl(paramsInstance);
      btnDescargar.dataset.pdfName = buildPdfFilename(paramsInstance);
      if (btnDescargar.dataset.autoDownload === "1") {
        btnDescargar.click();
      }
    }
  }

  try {
    await cargarVistaPreviaReporteVentas(params);
  } catch (err) {
    cont.innerHTML = `<div class="alert alert-danger mb-0">Error al generar la vista previa: ${err.message}</div>`;
    const modal = new bootstrap.Modal(modalEl);
    modal.show();
  }
});

document.addEventListener("click", async function (e) {
  const btn = e.target.closest("#btnDescargarReporteVentas");
  if (!btn) return;

  const cont = document.getElementById("contenidoVistaPreviaReporte");
  if (!cont) return;

  const sheet = cont.querySelector(".invoice-sheet-premium");
  if (!sheet) {
    Swal.fire({
      icon: "warning",
      title: "Sin vista previa",
      text: "Primero genera la vista previa del reporte.",
    });
    return;
  }

  const excelUrl = btn.dataset.excelUrl || "";
  const pdfName = btn.dataset.pdfName || "reporte_ventas.pdf";
  const autoDownload = btn.dataset.autoDownload === "1";
  const autoFormat = (btn.dataset.autoFormat || "").toLowerCase();

  function waitForImages(root) {
    const images = Array.from(root.querySelectorAll("img"));
    return Promise.all(
      images.map((img) => {
        if (img.complete && img.naturalWidth > 0) return Promise.resolve();
        return new Promise((resolve) => {
          const done = () => resolve();
          img.addEventListener("load", done, { once: true });
          img.addEventListener("error", done, { once: true });
        });
      })
    );
  }

  async function descargarPreviewComoPDF() {
    if (typeof html2pdf === "undefined") {
      throw new Error("html2pdf.js no está disponible.");
    }

    const wrapper = document.createElement("div");
    wrapper.style.position = "fixed";
    wrapper.style.left = "-99999px";
    wrapper.style.top = "0";
    wrapper.style.width = "210mm";
    wrapper.style.background = "#ffffff";
    wrapper.style.zIndex = "-1";

    const clone = sheet.cloneNode(true);

    // Copiar contenido de canvases (Chart.js) a imágenes en el clon para que html2canvas lo renderice.
    const srcCanvases = Array.from(sheet.querySelectorAll("canvas"));
    const dstCanvases = Array.from(clone.querySelectorAll("canvas"));
    srcCanvases.forEach((srcCanvas, idx) => {
      const dstCanvas = dstCanvases[idx];
      if (!dstCanvas) return;

      try {
        const dataUrl = srcCanvas.toDataURL("image/png");
        const img = document.createElement("img");
        img.src = dataUrl;
        img.alt = "grafica";
        img.style.width = "100%";
        img.style.height = "auto";
        img.style.display = "block";
        dstCanvas.replaceWith(img);
      } catch (e) {
        // Si falla, dejar el canvas tal cual.
      }
    });

    clone.classList.add("pdf-export-sheet");
    clone.style.margin = "0";
    clone.style.boxShadow = "none";
    clone.style.border = "0";

    wrapper.appendChild(clone);
    document.body.appendChild(wrapper);

    try {
      await waitForImages(clone);
      const opt = {
        margin: [4, 4, 4, 4],
        filename: pdfName,
        image: { type: "jpeg", quality: 0.98 },
        html2canvas: {
          scale: 2,
          useCORS: true,
          backgroundColor: "#f7f0e8",
          scrollX: 0,
          scrollY: 0,
        },
        jsPDF: {
          unit: "mm",
          format: "a4",
          orientation: "portrait",
        },
        pagebreak: {
          mode: ["avoid-all", "css", "legacy"],
        },
      };
      await html2pdf().set(opt).from(clone).save();
    } finally {
      wrapper.remove();
    }
  }

  if (autoDownload && autoFormat === "pdf") {
    try {
      Swal.fire({
        title: "Generando PDF...",
        text: "Espera un momento",
        allowOutsideClick: false,
        didOpen: () => Swal.showLoading(),
      });

      await descargarPreviewComoPDF();
      Swal.close();
    } catch (error) {
      Swal.fire({
        icon: "error",
        title: "No se pudo descargar",
        text: error.message || "Error generando el PDF.",
      });
    } finally {
      delete btn.dataset.autoDownload;
      delete btn.dataset.autoFormat;
    }
    return;
  }

  let result;
  if (excelUrl) {
    result = await Swal.fire({
      title: "Descargar reporte",
      text: "Selecciona el formato",
      icon: "question",
      showCancelButton: true,
      showDenyButton: true,
      confirmButtonText: "PDF",
      denyButtonText: "Excel",
      cancelButtonText: "Cancelar",
      reverseButtons: true,
      buttonsStyling: false,
      customClass: {
        confirmButton: "btn btn-danger me-2",
        denyButton: "btn btn-success me-2",
        cancelButton: "btn btn-secondary",
      },
    });
  } else {
    result = await Swal.fire({
      title: "Descargar reporte",
      text: "Se descargará en PDF.",
      icon: "question",
      showCancelButton: true,
      confirmButtonText: "PDF",
      cancelButtonText: "Cancelar",
      reverseButtons: true,
      buttonsStyling: false,
      customClass: {
        confirmButton: "btn btn-danger me-2",
        cancelButton: "btn btn-secondary",
      },
    });
  }

  if (result.isConfirmed) {
    try {
      Swal.fire({
        title: "Generando PDF...",
        text: "Espera un momento",
        allowOutsideClick: false,
        didOpen: () => Swal.showLoading(),
      });

      await descargarPreviewComoPDF();
      Swal.close();
    } catch (error) {
      Swal.fire({
        icon: "error",
        title: "No se pudo descargar",
        text: error.message || "Error generando el PDF.",
      });
    }
  } else if (result.isDenied) {
    if (!excelUrl) {
      Swal.fire({
        icon: "warning",
        title: "Sin archivo",
        text: "No se encontró la ruta del Excel.",
      });
      return;
    }
    window.location.href = excelUrl;
  }
});
document.addEventListener("submit", function (e) {
  const form = e.target;
  if (!form.matches("#formReporteVentas")) return;

  e.preventDefault();

  const columnas = form.querySelectorAll('input[name="columnas"]:checked');
  if (columnas.length === 0) {
    Swal.fire({
      icon: "warning",
      title: "Selecciona al menos una columna",
    });
    return;
  }

  if (!validarFechasReporte(form)) {
    Swal.fire({
      icon: "warning",
      title: "Revisa las fechas",
      text: "Corrige los errores en las fechas antes de continuar.",
      confirmButtonColor: "#8d604a",
    });
    return;
  }

  const params = new URLSearchParams(new FormData(form));
  const formato = (params.get("formato") || "pdf").toLowerCase();

  if (formato === "excel") {
    window.location.href = `/ventas/reporte/exportar/?${params.toString()}`;
    return;
  }

  // PDF: generar vista previa premium y descargar desde HTML (igual que Compras)
  const btnPreview = document.getElementById("btnVistaPreviaReporte");
  if (btnPreview) {
    const btnDescargar = document.getElementById("btnDescargarReporteVentas");
    if (btnDescargar) {
      btnDescargar.dataset.autoDownload = "1";
      btnDescargar.dataset.autoFormat = "pdf";
    }
    btnPreview.click();
  } else {
    Swal.fire({
      icon: "error",
      title: "No se pudo generar el PDF",
      text: "No se encontró el botón de vista previa.",
    });
  }
});
document.addEventListener("change", function (e) {
  const checkGrafica = e.target.closest('input[name="incluir_grafica"]');
  if (!checkGrafica) return;

  const bloqueTipo = document.getElementById("bloqueTipoGraficaVentas");
  if (!bloqueTipo) return;

  const checkComparativo = document.getElementById("checkComparativoVentas");
  const comparativoActivo = !!(checkComparativo && checkComparativo.checked);

  if (checkGrafica.checked && comparativoActivo) {
    bloqueTipo.classList.remove("d-none");
  } else {
    bloqueTipo.classList.add("d-none");
  }
});
// ============================================================
// 6) DEVOLUCION DE VENTAS
// ============================================================

let _urlRegistrarDevolucion = null;

document.addEventListener("click", async function (e) {
  const btn = e.target.closest(".btn-devolucion");
  if (!btn) return;

  _urlRegistrarDevolucion = btn.dataset.urlRegistrar;

  const cont   = document.getElementById("contenidoDevolucion");
  const footer = document.getElementById("footerDevolucion");
  if (!cont || !footer) return;

  cont.innerHTML = '<div class="text-center text-muted py-4"><div class="spinner-border spinner-border-sm me-2"></div>Cargando items...</div>';
  footer.classList.add("d-none");

  try {
    const res = await fetch(btn.dataset.url);
    if (!res.ok) {
      const err = await res.json().catch(function() { return {}; });
      throw new Error(err.error || "HTTP " + res.status);
    }
    const data = await res.json();

    // Validar: si todos los items son servicios, mostrar SweetAlert sin abrir modal
    var soloServicios = data.items.length > 0 && data.items.every(function(i) { return i.tipo === "servicio"; });
    if (soloServicios) {
      Swal.fire({
        icon: "info",
        title: "No aplica devolucion",
        html: "Esta venta solo contiene <strong>servicios</strong>.<br>Los servicios ya realizados no pueden ser devueltos.",
        confirmButtonText: "Entendido",
        confirmButtonColor: "#8d604a",
      });
      return;
    }

    // Abrir modal solo si hay productos devolvibles
    var modalEl = document.getElementById("modalDevolucion");
    var modal = new bootstrap.Modal(modalEl);
    renderFormDevolucion(cont, footer, data);
    modal.show();
  } catch (err) {
    cont.innerHTML = '<div class="alert alert-danger mb-0"><i class="bi bi-exclamation-triangle me-1"></i>' + err.message + '</div>';
  }
});


function renderFormDevolucion(cont, footer, data) {
  var yaDevueltoHtml = "";
  if (data.total_ya_devuelto > 0) {
    yaDevueltoHtml = '<div class="d-flex align-items-center gap-2 p-2 rounded-3 mb-3" style="background:rgba(141,96,74,0.08);border:1px solid rgba(141,96,74,0.2)">'
      + '<i class="bi bi-info-circle" style="color:#8d604a;font-size:1rem"></i>'
      + '<span style="color:#3a2117;font-size:.875rem">Esta venta ya tiene devoluciones previas por <strong>$' + data.total_ya_devuelto.toFixed(2) + '</strong>.</span>'
      + '</div>';
  }

  var filas = data.items.map(function(item) {
    var esServicio = item.tipo === "servicio";
    var sinStock = item.disponible === 0;
    var tipoIcon = !esServicio
      ? '<i class="bi bi-box-seam me-1" style="color:#8d604a"></i>'
      : '<i class="bi bi-scissors me-1" style="color:#8d604a"></i>';

    var disponibleBadge, accion, trOpacity;

    if (esServicio) {
      disponibleBadge = '<span class="text-muted small">—</span>';
      accion = '<span class="badge rounded-pill" style="background:rgba(100,100,100,0.09);color:#6c757d;font-size:.75rem">No aplica</span>';
      trOpacity = "opacity:.5";
    } else if (sinStock) {
      disponibleBadge = '<span class="badge rounded-pill" style="background:rgba(141,96,74,0.12);color:#8d604a;font-weight:600">0</span>';
      accion = '<span class="badge rounded-pill" style="background:rgba(141,96,74,0.10);color:#8d604a;font-size:.75rem">Completado</span>';
      trOpacity = "opacity:.55";
    } else {
      disponibleBadge = '<span class="badge rounded-pill" style="background:rgba(22,101,52,0.10);color:#166534;font-weight:600">' + item.disponible + '</span>';
      accion = '<input type="number" class="form-control form-control-sm text-center input-cant-dev" data-detalle="' + item.detalle_id + '" data-precio="' + item.precio_unitario + '" data-disponible="' + item.disponible + '" min="0" max="' + item.disponible + '" value="0" style="width:80px;margin:auto;border-color:rgba(141,96,74,0.3)">';
      trOpacity = "";
    }

    return '<tr style="' + trOpacity + '">'
      + '<td class="fw-medium">' + tipoIcon + item.nombre + '</td>'
      + '<td class="text-center">' + (esServicio ? '<span class="text-muted small">—</span>' : item.cantidad_original) + '</td>'
      + '<td class="text-center text-muted">' + (esServicio ? '<span class="text-muted small">—</span>' : item.ya_devuelto) + '</td>'
      + '<td class="text-center">' + disponibleBadge + '</td>'
      + '<td class="text-end fw-medium">$' + item.precio_unitario.toFixed(2) + '</td>'
      + '<td class="text-center" style="width:120px">' + accion + '</td>'
      + '</tr>';
  }).join("");

  cont.innerHTML = '<div class="d-flex flex-wrap gap-3 mb-3 p-3 rounded-3" style="background:rgba(141,96,74,0.06);border:1px solid rgba(141,96,74,0.15)">'
    + '<div><span class="text-muted small d-block" style="font-size:.72rem;text-transform:uppercase;letter-spacing:.04em">Venta</span><strong style="color:#3a2117">' + data.codigo_venta + '</strong></div>'
    + '<div><span class="text-muted small d-block" style="font-size:.72rem;text-transform:uppercase;letter-spacing:.04em">Cliente</span><strong style="color:#3a2117">' + data.cliente + '</strong></div>'
    + '<div><span class="text-muted small d-block" style="font-size:.72rem;text-transform:uppercase;letter-spacing:.04em">Total venta</span><strong style="color:#3a2117">$' + data.total_venta.toFixed(2) + '</strong></div>'
    + '</div>'
    + yaDevueltoHtml
    + '<div class="table-responsive mb-3">'
    + '<table class="table table-sm table-hover align-middle mb-0">'
    + '<thead><tr>'
    + '<th style="background:#2c0909;color:#fff;font-size:.75rem;text-transform:uppercase;letter-spacing:.05em;font-weight:600;padding:10px 12px">Item</th>'
    + '<th class="text-center" style="background:#2c0909;color:#fff;font-size:.75rem;text-transform:uppercase;letter-spacing:.05em;font-weight:600;padding:10px 12px">Vendido</th>'
    + '<th class="text-center" style="background:#2c0909;color:#fff;font-size:.75rem;text-transform:uppercase;letter-spacing:.05em;font-weight:600;padding:10px 12px">Ya devuelto</th>'
    + '<th class="text-center" style="background:#2c0909;color:#fff;font-size:.75rem;text-transform:uppercase;letter-spacing:.05em;font-weight:600;padding:10px 12px">Disponible</th>'
    + '<th class="text-end" style="background:#2c0909;color:#fff;font-size:.75rem;text-transform:uppercase;letter-spacing:.05em;font-weight:600;padding:10px 12px">Precio unit.</th>'
    + '<th class="text-center" style="background:#2c0909;color:#fff;font-size:.75rem;text-transform:uppercase;letter-spacing:.05em;font-weight:600;padding:10px 12px">Cant. a devolver</th>'
    + '</tr></thead>'
    + '<tbody>' + filas + '</tbody>'
    + '<tfoot><tr style="background:rgba(141,96,74,0.06)">'
    + '<td colspan="5" class="text-end fw-semibold" style="color:#3a2117;font-size:.9rem">Total a devolver:</td>'
    + '<td class="text-center fw-bold" id="subtotalDevolucion" style="color:#8d604a;font-size:1rem">$0.00</td>'
    + '</tr></tfoot>'
    + '</table></div>'
    + '<div class="mb-1">'
    + '<label class="form-label fw-semibold mb-1" style="color:#3a2117;font-size:.875rem">Motivo de devolucion <span class="text-danger">*</span></label>'
    + '<textarea id="motivoDevolucion" class="form-control" rows="2" maxlength="500" placeholder="Ej: producto defectuoso, error en pedido..." style="border-color:rgba(141,96,74,0.3);border-radius:10px;resize:none"></textarea>'
    + '<div class="invalid-feedback" id="motivoDevolucionError">El motivo es obligatorio.</div>'
    + '</div>';

  footer.classList.remove("d-none");

  cont.querySelectorAll(".input-cant-dev").forEach(function(inp) {
    inp.addEventListener("input", function() {
      recalcularSubtotalDevolucion(cont);
    });
  });
}


function recalcularSubtotalDevolucion(cont) {
  var total = 0;
  cont.querySelectorAll(".input-cant-dev").forEach(function(inp) {
    var cant = parseInt(inp.value) || 0;
    var precio = parseFloat(inp.dataset.precio) || 0;
    if (cant > parseInt(inp.dataset.disponible)) {
      inp.value = inp.dataset.disponible;
      cant = parseInt(inp.dataset.disponible);
    }
    total += cant * precio;
  });
  var el = document.getElementById("subtotalDevolucion");
  if (el) el.textContent = "$" + total.toFixed(2);
}


document.addEventListener("click", async function (e) {
  const btn = e.target.closest("#btnConfirmarDevolucion");
  if (!btn) return;

  const cont   = document.getElementById("contenidoDevolucion");
  const motivo = document.getElementById("motivoDevolucion");

  if (!motivo || !motivo.value.trim()) {
    if (motivo) motivo.classList.add("is-invalid");
    if (motivo) motivo.focus();
    return;
  }
  motivo.classList.remove("is-invalid");

  var items = [];
  cont.querySelectorAll(".input-cant-dev").forEach(function(inp) {
    var cant = parseInt(inp.value) || 0;
    if (cant > 0) {
      items.push({ detalle_id: parseInt(inp.dataset.detalle), cantidad: cant });
    }
  });

  if (items.length === 0) {
    if (typeof Swal !== "undefined") {
      Swal.fire({ icon: "warning", title: "Ingresa al menos una cantidad mayor a 0." });
    }
    return;
  }

  var subtotalEl = document.getElementById("subtotalDevolucion");
  var subtotal = subtotalEl ? subtotalEl.textContent : "";

  var confirm = await Swal.fire({
    icon: "warning",
    title: "Confirmar devolucion",
    html: "Se registrara una devolucion por <strong>" + subtotal + "</strong>.<br>Esta accion no se puede deshacer.",
    showCancelButton: true,
    confirmButtonText: "Si, registrar",
    cancelButtonText: "Cancelar",
    confirmButtonColor: "#f0a500",
    reverseButtons: true,
  });

  if (!confirm.isConfirmed) return;

  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Procesando...';

  try {
    var csrfToken = (document.querySelector("[name=csrfmiddlewaretoken]") || {}).value || getCookie("csrftoken");

    const res = await fetch(_urlRegistrarDevolucion, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify({ motivo: motivo.value.trim(), items: items }),
    });

    const data = await res.json();

    if (res.ok && data.ok) {
      var modalEl = document.getElementById("modalDevolucion");
      var modal = bootstrap.Modal.getInstance(modalEl);
      if (modal) modal.hide();

      var extraMsg = data.venta_anulada
        ? "<br><span class=\"badge bg-warning text-dark mt-2\">Venta anulada automaticamente</span>"
        : "";
      await Swal.fire({
        icon: "success",
        title: "Devolucion registrada",
        html: "<strong>" + data.codigo_devolucion + "</strong><br>Total devuelto: <strong>$" + data.total_devuelto.toFixed(2) + "</strong>" + extraMsg,
        timer: 3000,
        showConfirmButton: false,
      });

      location.reload();
    } else {
      Swal.fire({ icon: "error", title: "Error", text: data.error || "No se pudo registrar la devolucion." });
      btn.disabled = false;
      btn.innerHTML = '<i class="bi bi-check-circle me-1"></i> Confirmar devolucion';
    }
  } catch (err) {
    Swal.fire({ icon: "error", title: "Error de conexion", text: err.message });
    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-check-circle me-1"></i> Confirmar devolucion';
  }
});


function getCookie(name) {
  var value = "; " + document.cookie;
  var parts = value.split("; " + name + "=");
  if (parts.length === 2) return parts.pop().split(";").shift();
  return "";
}

// ============================================================
// BOTÓN X MODAL DEVOLUCIÓN — GIRO HORARIO/ANTIHORARIO
// ============================================================
document.addEventListener("mouseleave", function(e) {
  if (!e.target.closest) return;
  var btn = e.target.closest(".btn-close-dev");
  if (!btn) return;
  var icon = btn.querySelector(".btn-close-dev__icon");
  if (!icon) return;

  // Quitar clase hover-like y aplicar giro antihorario
  icon.classList.remove("spin-reset");
  icon.classList.add("spin-back");

  // Después de la transición, resetear a 0 sin animación
  setTimeout(function() {
    icon.classList.remove("spin-back");
    icon.classList.add("spin-reset");
    // Micro-tick para que el browser procese el cambio
    requestAnimationFrame(function() {
      requestAnimationFrame(function() {
        icon.classList.remove("spin-reset");
      });
    });
  }, 360);
}, true);
