function escapeHtml(str) {
  return String(str ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function getCSRFToken() {
  const el = document.querySelector('[name=csrfmiddlewaretoken]');
  return el ? el.value : "";
}

/** POST que NO rompe cuando es 409 (porque necesitamos leer el JSON) */
async function postAction(url, action, extra = {}) {
  const formData = new FormData();
  formData.append("action", action);
  Object.entries(extra).forEach(([k, v]) => formData.append(k, v));

  const res = await fetch(url, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "X-CSRFToken": getCSRFToken(),
      "X-Requested-With": "XMLHttpRequest",
    },
    body: formData,
  });

  let data = {};
  try {
    data = await res.json();
  } catch {
    data = {};
  }

  return { ok: res.ok, status: res.status, data };
}

function getRelacionItems(data) {
  if (Array.isArray(data?.detalles) && data.detalles.length) {
    const items = data.detalles.map((d, i) => ({
      id: i + 1,
      title: `${d.cantidad ?? ""} ${d.nombre ?? ""}`.trim(),
      meta: "",
    }));
    return { label: "Relaciones", count: items.length, items };
  }

  // Formato nuevo: data.related.detalle_compras.items = [...]
  const dc = data?.related?.detalle_compras;
  if (dc && Array.isArray(dc.items)) {
    const items = dc.items.map((it) => ({
      id: it.id,
      title: [
        it.compra_id ? `Compra #${it.compra_id}` : null,
        it.fecha ? it.fecha : null,
      ].filter(Boolean).join(" — "),
      meta: [
        it.cantidad != null ? `Cant: ${it.cantidad}` : null,
        it.precio != null ? `Precio: ${it.precio}` : null,
      ].filter(Boolean).join(" · "),
    }));
    return { label: "Detalle compras", count: dc.count ?? items.length, items };
  }

  return { label: "Relaciones", count: 0, items: [] };
}

/** Render interactivo: muestra 3 y botón ver más */
function renderInteractiveRelacionados(data, limit = 3) {
  const rel = getRelacionItems(data);
  const items = rel.items || [];
  const count = rel.count ?? items.length;

  if (!items.length) {
    return `<div class="text-muted">No se encontraron detalles para mostrar.</div>`;
  }

  const preview = items.slice(0, limit);
  const rest = items.slice(limit);

  const renderItem = (it) => `
    <div style="padding:8px 10px;border:1px solid #eee;border-radius:10px;margin:6px 0;">
      <div style="font-weight:600">${escapeHtml(it.title || `#${it.id}`)}</div>
      ${it.meta ? `<div style="opacity:.75;font-size:13px;margin-top:2px;">${escapeHtml(it.meta)}</div>` : ""}
    </div>
  `;

  const moreId = `swal_more_${Math.random().toString(16).slice(2)}`;

  return `
    <div style="text-align:left;">
      <div style="margin-bottom:8px;">
        <b>• ${escapeHtml(rel.label)}</b>
        <span style="opacity:.7">(${escapeHtml(count)})</span>
      </div>

      ${preview.map(renderItem).join("")}

      ${
        rest.length
          ? `
          <button id="${moreId}" type="button"
                  style="border:none;background:transparent;color:#0d6efd;padding:0;margin-top:6px;font-weight:600;">
            Ver más (${rest.length})
          </button>
          <div id="${moreId}_box" style="display:none;margin-top:6px;">
            ${rest.map(renderItem).join("")}
          </div>
        `
          : ""
      }
    </div>
  `;
}

/** Conecta el botón Ver más dentro del Swal */
function wireSwalMoreButton() {
  const btn = document.querySelector('[id^="swal_more_"]:not([id$="_box"])');
  if (!btn) return;

  const box = document.getElementById(btn.id + "_box");
  if (!box) return;

  btn.addEventListener("click", () => {
    const open = box.style.display !== "none";
    box.style.display = open ? "none" : "block";
    btn.textContent = open ? "Ver más" : "Ocultar";
  });
}
document.addEventListener("click", async (e) => {
  const btn = e.target.closest('button[data-url].btn-action-round');
  if (!btn) return;

  e.preventDefault();

  const url = btn.dataset.url;
  const toggleUrl = btn.dataset.toggleUrl || url.replace("/eliminar/", "/toggle-activo/");
  const nombre = btn.dataset.nombre || "este producto";
  const activo = btn.dataset.activo === "1";

  // CSRF (usa tu helper si ya lo tienes)
  const csrf =
    document.querySelector('input[name="csrfmiddlewaretoken"]')?.value ||
    document.cookie.split("; ").find(r => r.startsWith("csrftoken="))?.split("=")[1] ||
    "";

  // Confirmación
  const r = await Swal.fire({
    title: activo ? "¿Eliminar producto?" : "¿Reactivar producto?",
    text: activo
      ? `Se intentará eliminar "${nombre}". Si está relacionado, te ofrecerá desactivarlo.`
      : `Se reactivará "${nombre}".`,
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: activo ? "Sí, eliminar" : "Sí, reactivar",
    cancelButtonText: "Cancelar",
    confirmButtonColor: "#8b5a3c",
  });

  if (!r.isConfirmed) return;

  // Acción según estado
  const action = activo ? "delete" : "toggle";

  try {
    const requestUrl = action === "toggle" ? toggleUrl : url;
    const formData = new FormData();
    if (action === "delete") {
      formData.append("action", action);
    }

    const resp = await fetch(requestUrl, {
      method: "POST",
      body: formData,
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": csrf,
      },
      credentials: "same-origin",
    });

    const data = await resp.json().catch(() => ({}));

    // ✅ OK
    const fueExitoso =
      (data && data.success === true) ||
      data.status === "deleted" ||
      data.status === "activated" ||
      data.status === "inactivated";

    if (resp.ok && fueExitoso) {
      await Swal.fire({
        title:
          data.status === "deleted"
            ? "Eliminado"
            : data.status === "inactivated" || data.activo === false
              ? "Desactivado"
              : "Reactivado",
        icon: "success",
        confirmButtonColor: "#8b5a3c",
      });
      window.location.reload();
      return;
    }

    // ✅ PROTEGIDO => ofrecer desactivar
  if (resp.status === 409 || data.status === "protected") {
      const r2 = await Swal.fire({
        title: data.title || "No se puede eliminar",
        html: `
          <div>${data.message || "Está relacionado con otros registros."}</div>
          <div style="margin-top:10px;">¿Deseas desactivarlo en su lugar?</div>
        `,
        icon: "info",
        showCancelButton: true,
        confirmButtonText: "Sí, desactivar",
        cancelButtonText: "Cancelar",
        confirmButtonColor: "#8b5a3c",
      });

      if (!r2.isConfirmed) return;

      const resp2 = await fetch(toggleUrl, {
        method: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": csrf,
        },
        credentials: "same-origin",
      });

      const data2 = await resp2.json().catch(() => ({}));

      if (resp2.ok && (data2.status === "inactivated" || data2.activo === false)) {
        await Swal.fire({
          title: "Desactivado",
          text: "El producto fue desactivado correctamente.",
          icon: "success",
          confirmButtonColor: "#8b5a3c",
        });
        window.location.reload();
        return;
      }
    }

    // ❌ Error genérico
    await Swal.fire("Error", data.message || "No se pudo procesar la solicitud.", "error");
  } catch (err) {
    console.error(err);
    await Swal.fire("Error", "Ocurrió un error procesando la solicitud.", "error");
  }
});
