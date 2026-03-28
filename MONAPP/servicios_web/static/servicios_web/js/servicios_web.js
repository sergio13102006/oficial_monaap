/* ═══════════════════════════════════════════════
   servicios_web.js
   - initServiciosWeb() se llama en DOMContentLoaded
     Y tras cada actualización AJAX del partial
═══════════════════════════════════════════════ */

document.addEventListener("DOMContentLoaded", () => {

    /* ── Elementos fijos (nunca se destruyen con AJAX) ── */
    const modalEl    = document.getElementById("modalServicioWeb");
    const modalBody  = document.getElementById("modalBodyContent");
    const modalTitle = document.getElementById("modalServicioWebLabel");

    let modalInstance = modalEl ? new bootstrap.Modal(modalEl) : null;

    const previewModalEl    = document.getElementById("modalPreviewMedia");
    const previewModalBody  = document.getElementById("modalPreviewMediaBody");
    const previewModalLabel = document.getElementById("modalPreviewMediaLabel");
    const previewModal      = previewModalEl ? new bootstrap.Modal(previewModalEl) : null;

    let lastPreviewServicioId = null;
    let lastPreviewMode       = "image";

    /* ══════════════════════════════════════════════════
       HELPERS
    ══════════════════════════════════════════════════ */
    function getCSRFToken() {
        const c = document.cookie.split("; ").find(r => r.startsWith("csrftoken="));
        return c ? c.split("=")[1] : "";
    }

    function buildModalUrl(url) {
        return url + (url.includes("?") ? "&" : "?") + "modal=1";
    }

    const INPUT_RULES = {
        textoSeguro: /[A-Za-z0-9ÁÉÍÓÚáéíóúÑñ\s]/,
        precio: /[0-9.,]/,
    };

    function sanitizeByRule(value, rule) {
        return Array.from(value || "").filter(ch => rule.test(ch)).join("");
    }

    function bindRestrictedInput(input, rule, sanitizeFn) {
        if (!input || input.dataset.restrictionBound === "1") return;
        input.dataset.restrictionBound = "1";

        input.addEventListener("beforeinput", (event) => {
            if (!event.data || event.inputType?.startsWith("delete")) return;
            if (!rule.test(event.data)) event.preventDefault();
        });

        input.addEventListener("paste", (event) => {
            const text = event.clipboardData?.getData("text") || "";
            const clean = sanitizeFn(text);
            if (clean === text) return;
            event.preventDefault();
            const start = input.selectionStart ?? input.value.length;
            const end = input.selectionEnd ?? input.value.length;
            input.value = `${input.value.slice(0, start)}${clean}${input.value.slice(end)}`;
            input.dispatchEvent(new Event("input", { bubbles: true }));
        });

        input.addEventListener("input", () => {
            const clean = sanitizeFn(input.value);
            if (clean !== input.value) {
                const start = input.selectionStart;
                input.value = clean;
                if (typeof start === "number") {
                    input.setSelectionRange(Math.min(start, clean.length), Math.min(start, clean.length));
                }
            }
        });
    }

    /* ══════════════════════════════════════════════════
       MODAL FORM (crear / editar)
    ══════════════════════════════════════════════════ */
    async function abrirModalDesdeURL(url, titulo = "Servicio Web") {
        if (!modalEl || !modalBody) return;

        modalBody.innerHTML = `<div class="text-center p-5"><div class="spinner-border text-primary" role="status"></div></div>`;
        if (modalTitle) modalTitle.innerHTML = `<i class="fas fa-plus me-2"></i> ${titulo}`;
        modalInstance.show();

        try {
            const r = await fetch(buildModalUrl(url), { headers: { "X-Requested-With": "XMLHttpRequest" } });
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            modalBody.innerHTML = await r.text();
            bindModalForm();
        } catch (err) {
            console.error("Error cargando formulario:", err);
            modalBody.innerHTML = `<div class="alert alert-danger m-3">No se pudo cargar el formulario.</div>`;
        }
    }

    function bindModalForm() {
        const form = modalBody?.querySelector("form");
        if (!form) return;

        const isEdit      = form.dataset.isEdit === "1";
        const servicioId  = form.dataset.servicioId || "";
        const nombreInput = form.querySelector('input[name="nombre"]');
        const descInput   = form.querySelector('textarea[name="descripcion"]');
        const precioInput = form.querySelector('input[name="precio"]');
        const imagenInput = form.querySelector('input[name="imagen"]');
        const videoInput  = form.querySelector('input[name="video"]');
        const btnGuardar  = form.querySelector("#btnGuardarServicioWeb");

        let nombreTimer = null;
        let videoDurationValida = true;

        bindRestrictedInput(nombreInput, INPUT_RULES.textoSeguro, value => sanitizeByRule(value, INPUT_RULES.textoSeguro));
        bindRestrictedInput(descInput, INPUT_RULES.textoSeguro, value => sanitizeByRule(value, INPUT_RULES.textoSeguro));
        bindRestrictedInput(precioInput, INPUT_RULES.precio, value => sanitizeByRule(value, INPUT_RULES.precio));

        function setButtonState(enabled) {
            if (!btnGuardar) return;
            btnGuardar.disabled = !enabled;
            btnGuardar.classList.toggle("btn-secondary", !enabled);
            btnGuardar.classList.toggle("btn-primary", enabled);
        }

        function getFeedback(input) {
            if (!input) return null;
            const group = input.closest(".input-group");
            let next = (group || input).nextElementSibling;
            while (next) {
                if (next.classList?.contains("invalid-feedback")) return next;
                next = next.nextElementSibling;
            }
            return null;
        }

        function setInvalid(input, msg) {
            if (!input) return;
            input.classList.replace("is-valid", "is-invalid") || input.classList.add("is-invalid");
            const fb = getFeedback(input); if (fb) fb.textContent = msg || "";
        }
        function setValid(input) {
            if (!input) return;
            input.classList.replace("is-invalid", "is-valid") || input.classList.add("is-valid");
            const fb = getFeedback(input); if (fb) fb.textContent = "";
        }
        function clearState(input) {
            if (!input) return;
            input.classList.remove("is-invalid", "is-valid");
            const fb = getFeedback(input); if (fb) fb.textContent = "";
        }

        function isInputValid(input) {
            return !input || (input.classList.contains("is-valid") && !input.classList.contains("is-invalid"));
        }

        function updateSubmitState() {
            setButtonState(
                isInputValid(nombreInput) && isInputValid(descInput) && isInputValid(precioInput) &&
                (!imagenInput || !imagenInput.classList.contains("is-invalid")) &&
                (!videoInput  || (!videoInput.classList.contains("is-invalid") && videoDurationValida))
            );
        }

        async function validarNombre() {
            const v = (nombreInput?.value || "").trim();
            if (!v)              { setInvalid(nombreInput, "El nombre es obligatorio.");    updateSubmitState(); return false; }
            if (v.length < 3)    { setInvalid(nombreInput, "Mínimo 3 caracteres.");         updateSubmitState(); return false; }
            if (!/^[A-Za-z0-9ÁÉÍÓÚáéíóúÑñ\s]+$/.test(v)) {
                setInvalid(nombreInput, "Contiene caracteres no permitidos."); updateSubmitState(); return false;
            }
            return new Promise(resolve => {
                if (nombreTimer) clearTimeout(nombreTimer);
                nombreTimer = setTimeout(async () => {
                    try {
                        const r = await fetch(`/servicios_web/validar-nombre/?nombre=${encodeURIComponent(v)}&servicio_id=${encodeURIComponent(servicioId)}`, { headers: { "X-Requested-With": "XMLHttpRequest" } });
                        const d = await r.json();
                        d.valido ? setValid(nombreInput) : setInvalid(nombreInput, d.mensaje || "Nombre no válido.");
                    } catch { setInvalid(nombreInput, "No se pudo validar el nombre."); }
                    updateSubmitState();
                    resolve(isInputValid(nombreInput));
                }, 400);
            });
        }

        function validarDescripcion() {
            const v = (descInput?.value || "").trim();
            if (!v)           { setInvalid(descInput, "La descripción es obligatoria."); return false; }
            if (v.length < 10){ setInvalid(descInput, "Mínimo 10 caracteres.");          return false; }
            if (!/^[A-Za-z0-9ÁÉÍÓÚáéíóúÑñ\s]+$/.test(v)) {
                setInvalid(descInput, "Contiene caracteres no permitidos."); return false;
            }
            setValid(descInput); return true;
        }

        function validarPrecio() {
            const v = (precioInput?.value || "").trim();
            const n = parseFloat(v.replace(",", "."));
            if (!v)           { setInvalid(precioInput, "El precio es obligatorio.");  return false; }
            if (isNaN(n))     { setInvalid(precioInput, "Ingresa un precio válido.");  return false; }
            if (n <= 0)       { setInvalid(precioInput, "Debe ser mayor a 0.");        return false; }
            setValid(precioInput); return true;
        }

        function validarImagen() {
            if (!imagenInput?.files[0]) { clearState(imagenInput); return true; }
            if (!imagenInput.files[0].type.startsWith("image/")) { setInvalid(imagenInput, "Selecciona una imagen válida."); return false; }
            setValid(imagenInput); return true;
        }

        async function validarVideo() {
            if (!videoInput?.files[0]) { clearState(videoInput); videoDurationValida = true; return true; }
            const f = videoInput.files[0];
            const tipos = ["video/mp4","video/webm","video/ogg","video/quicktime"];
            if (!tipos.includes(f.type))      { setInvalid(videoInput, "Formato no permitido."); videoDurationValida = false; return false; }
            if (f.size > 25 * 1024 * 1024)   { setInvalid(videoInput, "Máximo 25 MB.");          videoDurationValida = false; return false; }
            return new Promise(resolve => {
                const v = document.createElement("video");
                v.preload = "metadata";
                v.onloadedmetadata = () => {
                    URL.revokeObjectURL(v.src);
                    if (v.duration > 20) { setInvalid(videoInput, "Máximo 20 segundos."); videoDurationValida = false; resolve(false); return; }
                    setValid(videoInput); videoDurationValida = true; resolve(true);
                };
                v.onerror = () => { URL.revokeObjectURL(v.src); setInvalid(videoInput, "No se pudo leer el video."); videoDurationValida = false; resolve(false); };
                v.src = URL.createObjectURL(f);
            });
        }

        nombreInput?.addEventListener("input",  () => validarNombre());
        descInput?.addEventListener("input",    () => { validarDescripcion(); updateSubmitState(); });
        precioInput?.addEventListener("input",  () => { validarPrecio(); updateSubmitState(); });
        imagenInput?.addEventListener("change", () => { validarImagen(); updateSubmitState(); });
        videoInput?.addEventListener("change",  async () => { await validarVideo(); updateSubmitState(); });

        if ((nombreInput?.value || "").trim()) validarNombre();
        if ((descInput?.value   || "").trim()) validarDescripcion();
        if ((precioInput?.value || "").trim()) validarPrecio();
        updateSubmitState();

        form.addEventListener("submit", async e => {
            e.preventDefault();
            const ok1 = await validarNombre();
            const ok2 = validarDescripcion();
            const ok3 = validarPrecio();
            const ok4 = validarImagen();
            const ok5 = await validarVideo();
            updateSubmitState();
            if (!(ok1 && ok2 && ok3 && ok4 && ok5)) {
                Swal.fire({ icon:"warning", title:"Formulario incompleto", text:"Corrige los campos marcados." });
                return;
            }
            const tieneImg   = imagenInput?.files?.length > 0;
            const tieneVideo = videoInput?.files?.length  > 0;
            if (!isEdit && !tieneImg && !tieneVideo) {
                const r = await Swal.fire({ title:"¿Guardar sin multimedia?", html:"Este servicio no tiene imagen ni video.<br>¿Continuar?", icon:"warning", showCancelButton:true, confirmButtonColor:"#2b2b2b", cancelButtonColor:"#6c757d", confirmButtonText:"Sí, guardar", cancelButtonText:"Cancelar", reverseButtons:true });
                if (!r.isConfirmed) return;
            }
            try {
                const r = await fetch(form.action + "?modal=1", { method:"POST", body: new FormData(form), headers:{ "X-Requested-With":"XMLHttpRequest" } });
                const d = await r.json();
                if (d.success) {
                    modalInstance.hide();
                    await Swal.fire({ icon:"success", title:"Servicio guardado", timer:1600, showConfirmButton:false });
                    window.location.reload();
                    return;
                }
                Swal.fire({ icon:"error", title:"No se pudo guardar", text:"Revisa los datos del formulario." });
            } catch { Swal.fire({ icon:"error", title:"No se pudo guardar", text:"Error al guardar el servicio." }); }
        });
    }

    /* ── Botón Nuevo (fuera del partial, no cambia con AJAX) ── */
    document.getElementById("btnOpenCrearServicioWeb")?.addEventListener("click", function () {
        abrirModalDesdeURL(this.dataset.url, "Nuevo Servicio Web");
    });

    /* ── Preview modal ── */
    function renderPreviewMedia({ nombre, imagen, video, mode }) {
        if (!previewModalBody || !previewModalLabel) return;
        previewModalLabel.textContent = nombre || "Vista previa";
        let content = "";
        if (mode === "video" && video) {
            content = `<div class="sw-preview-container"><div class="sw-preview-help">Vista de video</div><video class="sw-preview-media sw-preview-video" src="${video}" controls autoplay playsinline preload="metadata">Tu navegador no soporta video.</video></div>`;
        } else if (imagen) {
            content = `<div class="sw-preview-container ${video ? "sw-preview-clickable" : ""}" data-preview-nombre="${nombre||""}" data-preview-imagen="${imagen||""}" data-preview-video="${video||""}" data-preview-mode="image">${video ? '<div class="sw-preview-help">Click en la imagen para ver el video</div>' : ''}<img src="${imagen}" alt="${nombre}" class="sw-preview-media sw-preview-image"></div>`;
        } else if (video) {
            content = `<div class="sw-preview-container"><div class="sw-preview-help">Vista de video</div><video class="sw-preview-media sw-preview-video" src="${video}" controls autoplay playsinline preload="metadata">Tu navegador no soporta video.</video></div>`;
        } else {
            content = `<div class="sw-preview-empty"><i class="bi bi-image" style="font-size:3rem;"></i><p class="mt-3 mb-0">Sin imagen ni video.</p></div>`;
        }
        previewModalBody.innerHTML = content;
        previewModalBody.querySelector("video")?.play().catch(() => {});
        previewModalBody.querySelector(".sw-preview-clickable")?.addEventListener("click", function () {
            if (!this.dataset.previewVideo) return;
            renderPreviewMedia({ nombre: this.dataset.previewNombre, imagen: this.dataset.previewImagen, video: this.dataset.previewVideo, mode:"video" });
            lastPreviewMode = "video";
        });
    }

    previewModalEl?.addEventListener("hidden.bs.modal", () => {
        if (previewModalBody) previewModalBody.innerHTML = "";
        lastPreviewServicioId = null;
        lastPreviewMode = "image";
    });

    /* ══════════════════════════════════════════════════
       initServiciosWeb()
       Todo lo que depende de elementos del partial.
       Se llama en DOMContentLoaded Y tras cada AJAX.
    ══════════════════════════════════════════════════ */
    window.initServiciosWeb = function () {

        const serviciosWebView = document.getElementById("serviciosWebView");

        /* ── Vista guardada ── */
        function animarCardsGrid() {
            document.querySelectorAll("#servicesGrid .sq-card:not(.sw-hidden)").forEach((card, i) => {
                card.classList.remove("is-visible");
                setTimeout(() => card.classList.add("is-visible"), Math.min(i * 45, 360));
            });
        }

        function aplicarVista(view) {
            if (!serviciosWebView) return;
            serviciosWebView.dataset.view = view;
            localStorage.setItem("servicios_web_view_mode", view);
            document.querySelectorAll(".sw-view-btn").forEach(btn => btn.classList.toggle("active", btn.dataset.view === view));
            if (view !== "table") {
                animarCardsGrid();
                window.initMetaballs?.();
            }
        }

        document.querySelectorAll(".sw-view-btn").forEach(btn => {
            btn.addEventListener("click", () => aplicarVista(btn.dataset.view));
        });

        aplicarVista(localStorage.getItem("servicios_web_view_mode") || "grid-2");

        /* ── Videos en cards ── */
        function prepareVideo(video) {
            if (!video) return;
            video.muted = true; video.defaultMuted = true; video.playsInline = true;
            ["muted","playsinline","webkit-playsinline","preload"].forEach(a => video.setAttribute(a, a === "preload" ? "metadata" : ""));
        }

        function closeVideo(card, video) {
            if (!card || !video) return;
            card.classList.remove("playing");
            try { video.pause(); video.currentTime = 0; } catch {}
        }

        async function openVideo(card, video) {
            if (!card || !video) return;
            document.querySelectorAll(".sq-card.playing").forEach(c => { if (c !== card) closeVideo(c, c.querySelector("video.sq-video")); });
            prepareVideo(video);
            try { video.pause(); video.currentTime = 0; } catch {}
            try { await video.play(); card.classList.add("playing"); } catch {}
        }

        document.querySelectorAll(".sq-card").forEach(card => {
            const video = card.querySelector("video.sq-video");
            if (video) {
                prepareVideo(video);
                video.addEventListener("ended", () => closeVideo(card, video));
                video.addEventListener("loadeddata", () => card.classList.add("video-loaded"));
            }
            card.addEventListener("click", async e => {
                if (e.target.closest(".actions-overlay, .btn-action, button, a")) return;
                if (!video) return;
                card.classList.contains("playing") ? closeVideo(card, video) : await openVideo(card, video);
            });
        });

        /* ── Editar ── */
        document.querySelectorAll(".btn-edit-servicioweb").forEach(btn => {
            btn.addEventListener("click", e => {
                e.stopPropagation();
                abrirModalDesdeURL(btn.dataset.url, "Editar Servicio Web");
            });
        });

        /* ── Eliminar ── */
        document.querySelectorAll(".btn-delete-servicioweb").forEach(btn => {
            btn.addEventListener("click", async e => {
                e.stopPropagation();
                const nombre = btn.dataset.nombre || "este servicio";
                const result = await Swal.fire({ title:"¿Eliminar servicio web?", html:`Vas a eliminar <strong>${nombre}</strong>.<br>Esta acción no se puede deshacer.`, icon:"warning", showCancelButton:true, confirmButtonColor:"#dc3545", cancelButtonColor:"#6c757d", confirmButtonText:"Sí, eliminar", cancelButtonText:"Cancelar", reverseButtons:true, focusCancel:true });
                if (!result.isConfirmed) return;
                try {
                    const r = await fetch(btn.dataset.url, { method:"POST", headers:{ "X-Requested-With":"XMLHttpRequest", "X-CSRFToken": getCSRFToken() } });
                    if (!r.ok) throw new Error();
                    await Swal.fire({ icon:"success", title:"Servicio eliminado", timer:1500, showConfirmButton:false });
                    window.location.reload();
                } catch { Swal.fire({ icon:"error", title:"No se pudo eliminar", text:"Ocurrió un error." }); }
            });
        });

        /* ── Toggle activo ── */
        if (!window.__serviciosWebToggleBound) {
            window.__serviciosWebToggleBound = true;

            document.addEventListener("click", async (e) => {
                const btn = e.target.closest(".toggle-activo-servicioweb");
                if (!btn) return;

                e.preventDefault();
                e.stopPropagation();

                const url = btn.dataset.url;
                const activoActual = btn.dataset.activo === "true";
                const nombre = btn.dataset.nombre || "el servicio";

                if (!url) {
                    if (typeof Swal !== "undefined" && Swal.fire) {
                        Swal.fire({
                            icon: "error",
                            title: "No se pudo cambiar el estado",
                            text: "Falta la URL del cambio de estado.",
                            confirmButtonColor: "#2b2b2b",
                            confirmButtonText: "OK",
                        });
                    } else {
                        alert("Falta la URL del cambio de estado.");
                    }
                    return;
                }

                btn.disabled = true;

                try {
                    const r = await fetch(url, {
                        method: "POST",
                        credentials: "same-origin",
                        headers: {
                            "X-Requested-With": "XMLHttpRequest",
                            "X-CSRFToken": getCSRFToken()
                        }
                    });
                    const data = await r.json().catch(() => ({}));
                    if (!r.ok || !data.success) {
                        throw new Error(data.message || "No se pudo cambiar el estado del servicio.");
                    }

                    const activo = !!data.activo;
                    btn.dataset.activo = activo ? "true" : "false";

                    if (typeof Swal !== "undefined" && Swal.fire) {
                        await Swal.fire({
                            icon: "success",
                            title: activo ? "Servicio activado" : "Servicio inactivado",
                            text: activo
                                ? `${nombre} quedó activo.`
                                : `${nombre} quedó inactivo.`,
                            confirmButtonColor: "#2b2b2b",
                            confirmButtonText: "OK",
                        });
                    } else {
                        alert(activo ? `${nombre} quedó activo.` : `${nombre} quedó inactivo.`);
                    }

                    window.location.reload();
                } catch (error) {
                    if (typeof Swal !== "undefined" && Swal.fire) {
                        await Swal.fire({
                            icon: "error",
                            title: "No se pudo cambiar el estado",
                            text: error.message || "Intenta nuevamente.",
                            confirmButtonColor: "#2b2b2b",
                            confirmButtonText: "OK",
                        });
                    } else {
                        alert(error.message || "No se pudo cambiar el estado del servicio.");
                    }
                } finally {
                    btn.disabled = false;
                }
            });
        }

        /* ── Media trigger (tabla) ── */
        document.querySelectorAll(".sw-media-trigger").forEach(btn => {
            btn.addEventListener("click", () => {
                const servicioId = btn.dataset.servicioId;
                const nombre     = btn.dataset.nombre || "Vista previa";
                const imagen     = btn.dataset.imagen || "";
                const video      = btn.dataset.video  || "";
                let mode = "image";
                if (!imagen && video) mode = "video";
                else if (lastPreviewServicioId === servicioId && lastPreviewMode === "image" && video) mode = "video";
                renderPreviewMedia({ nombre, imagen, video, mode });
                lastPreviewServicioId = servicioId;
                lastPreviewMode = mode;
                previewModal?.show();
            });
        });

        /* ── Ordenar tabla ── */
        const sortState = {};
        document.querySelectorAll(".sw-sortable").forEach(header => {
            header.addEventListener("click", () => {
                const tbody = document.querySelector(".services-table-wrapper table tbody");
                if (!tbody) return;
                const key  = header.dataset.sortKey;
                const type = header.dataset.sortType || "text";
                const dir  = sortState[key] === "asc" ? "desc" : "asc";
                sortState[key] = dir;
                const rows = Array.from(tbody.querySelectorAll("tr")).sort((a, b) => {
                    let va = a.dataset[key] || "", vb = b.dataset[key] || "";
                    if (type === "number") { va = parseFloat(String(va).replace(/[^0-9.-]+/g,"")) || 0; vb = parseFloat(String(vb).replace(/[^0-9.-]+/g,"")) || 0; }
                    else { va = String(va).toLowerCase(); vb = String(vb).toLowerCase(); }
                    return va < vb ? (dir==="asc"?-1:1) : va > vb ? (dir==="asc"?1:-1) : 0;
                });
                rows.forEach(r => tbody.appendChild(r));
                document.querySelectorAll(".sw-sortable").forEach(th => {
                    const icon = th.querySelector("i");
                    if (!icon) return;
                    if (th === header) {
                        icon.className = dir==="asc" ? "bi bi-sort-down ms-1" : "bi bi-sort-up ms-1";
                        th.classList.toggle("sorted-asc",  dir==="asc");
                        th.classList.toggle("sorted-desc", dir==="desc");
                    } else {
                        icon.className = "bi bi-arrow-down-up ms-1";
                        th.classList.remove("sorted-asc","sorted-desc");
                    }
                });
            });
        });

        /* ── Animación entrada ── */
        document.body.classList.add("sw-enter-ready");
        requestAnimationFrame(() => requestAnimationFrame(() => {
            document.querySelectorAll(".sw-enter").forEach(el => el.classList.add("is-visible"));
            if ((serviciosWebView?.dataset.view || "") !== "table") animarCardsGrid();
        }));
    };

    /* Primera llamada */
    window.initServiciosWeb();

    /* Re-llamar tras cada actualización AJAX del partial */
    const wrap = document.getElementById("sw-resultados-wrap");
    if (wrap) {
        new MutationObserver(() => window.initServiciosWeb())
            .observe(wrap, { childList: true, subtree: false });
    }

    /* Animación del header de página */
    const pageHeader = document.querySelector(".page-header");
    if (pageHeader) requestAnimationFrame(() => pageHeader.classList.add("sw-intro-ready"));

});
