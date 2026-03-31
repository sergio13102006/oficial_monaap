
const PROMO_TAGS_MAP = {
    'success': { icon: 'success', background: '#f0fdf4', color: '#166534' },
    'error':   { icon: 'error',   background: '#fef2f2', color: '#991b1b' },
    'warning': { icon: 'warning', background: '#fffbeb', color: '#92400e' },
    'info':    { icon: 'info',    background: '#eff6ff', color: '#1e40af' },
};

function showPromoMessages(messages) {
    if (!messages || !messages.length) return;

    messages.forEach((m) => {
        const tag = Object.keys(PROMO_TAGS_MAP).find((k) => (m.tags || '').includes(k)) || 'info';
        const opts = PROMO_TAGS_MAP[tag];
        Swal.fire({
            icon: opts.icon,
            title: tag === 'success' ? 'Éxito' : (tag === 'error' ? 'Error' : 'Información'),
            text: m.text,
            confirmButtonColor: '#3a2a24',
            timer: 3000,
            timerProgressBar: true,
        });
    });
}

function initPromoFilterMenu() {
    document.addEventListener('click', function (e) {
        const action = e.target.closest('[data-promo-action]');
        if (action) {
            const type = action.dataset.promoAction;
            if (type === 'toggle-filter') {
                const menu = action.closest('.custom-select-wrapper')?.querySelector('.custom-select-options');
                if (!menu) return;
                document.querySelectorAll('.custom-select-options').forEach((m) => {
                    if (m !== menu) m.style.display = 'none';
                });
                menu.style.display = (menu.style.display === 'block') ? 'none' : 'block';
                return;
            }

            if (type === 'select-filter') {
                const wrapper = action.closest('.custom-select-wrapper');
                const input = wrapper?.querySelector('input[type="hidden"]');
                const labelEl = wrapper?.querySelector('.custom-select-label');
                const form = action.closest('form');
                if (!wrapper || !input || !labelEl) return;

                input.value = action.dataset.filterValue || '';
                labelEl.innerText = action.dataset.filterLabel || 'Estado';
                wrapper.querySelectorAll('.custom-select-option').forEach((opt) => opt.classList.remove('active'));
                action.classList.add('active');
                wrapper.querySelector('.custom-select-options').style.display = 'none';

                if (form && form._submitAjaxSearch) {
                    form._submitAjaxSearch(true);
                } else if (form) {
                    form.submit();
                }
                return;
            }
        }

        if (!e.target.closest('.custom-select-wrapper')) {
            document.querySelectorAll('.custom-select-options').forEach((menu) => {
                menu.style.display = 'none';
            });
        }
    });
}

function initPromoForm(form) {
    if (!form || form.dataset.promoWired === '1') return;
    form.dataset.promoWired = '1';

    const validarUrl = form.dataset.validarNombreUrl || '';
    const nombreInput = form.querySelector('[name="nombre"]');
    const descInput = form.querySelector('[name="porcentaje_descuento"]');
    const inicioInput = form.querySelector('[name="fecha_inicio"]');
    const finInput = form.querySelector('[name="fecha_fin"]');
    const descripcion = form.querySelector('[name="descripcion"]');
    const fileInput = form.querySelector('input[type="file"][name="imagen"]');
    const preview = form.querySelector('#previewPromo, #previewPromoModal, #previewPromoEdit');
    const dropzone = form.querySelector('#dropzonePromo, #dropzonePromoModal, #dropzonePromoEdit');
    const removeImageBtn = form.querySelector('#btnRemoveImageEdit');

    const errNombre = form.querySelector('#err_nombre_promo_form, #err_nombre_ag, #err_nombre_ed');
    const iconNombre = form.querySelector('#icon_nombre_form, #icon_nombre_ag');
    const errDesc = form.querySelector('#err_descuento_form, #err_desc_ag, #err_desc_ed');
    const iconDesc = form.querySelector('#icon_descuento_form');
    const errInicio = form.querySelector('#err_inicio_form, #err_inicio_ag, #err_inicio_ed');
    const errFin = form.querySelector('#err_fin_form, #err_fin_ag, #err_fin_ed');
    const charDesc = form.querySelector('#char_desc_form, #char_desc_ag');

    const isEdit = !!form.querySelector('#edit_nombre, #edit_descuento, #edit_inicio, #edit_fin');

    function promoErr(input, errEl, msg, iconEl) {
        if (!input || !errEl) return false;
        if (msg) {
            input.classList.add('is-invalid-promo');
            input.classList.remove('is-valid-promo');
            errEl.textContent = msg;
            errEl.classList.add('visible');
            if (iconEl) {
                iconEl.classList.remove('show', 'valid', 'invalid', 'bi-check-lg', 'bi-exclamation-lg');
                iconEl.classList.add('show', 'invalid', 'bi-exclamation-lg');
            }
            return false;
        }
        input.classList.remove('is-invalid-promo');
        input.classList.add('is-valid-promo');
        errEl.textContent = '';
        errEl.classList.remove('visible');
        if (iconEl) {
            iconEl.classList.remove('show', 'valid', 'invalid', 'bi-check-lg', 'bi-exclamation-lg');
            iconEl.classList.add('show', 'valid', 'bi-check-lg');
        }
        return true;
    }

    function promoContador(textarea, contEl, max) {
        if (!textarea || !contEl) return;
        const len = textarea.value.length;
        if (len > max) textarea.value = textarea.value.substring(0, max);
        contEl.textContent = `${Math.min(len, max)}/${max} caracteres`;
        contEl.className = 'promo-char-count' + (len >= max ? ' at-limit' : len >= max * 0.85 ? ' near-limit' : '');
    }

    function promoFmtLocalDate(d) {
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return `${y}-${m}-${day}`;
    }

    function promoMaxInicio() {
        const d = new Date();
        const originalDay = d.getDate();
        d.setFullYear(d.getFullYear() + 1);
        if (d.getDate() !== originalDay) d.setDate(0);
        return promoFmtLocalDate(d);
    }

    function promoMinDate() {
        const d = new Date();
        const originalDay = d.getDate();
        d.setFullYear(d.getFullYear() - 1);
        if (d.getDate() !== originalDay) d.setDate(0);
        return promoFmtLocalDate(d);
    }

    function validarNombrePromo() {
        if (!nombreInput || !errNombre) return true;
        const v = nombreInput.value.trim();
        let msg = '';
        if (!v) msg = 'El nombre es obligatorio.';
        else if (v.length < 2) msg = 'Mínimo 2 caracteres.';
        else if (v.length > 200) msg = 'Máximo 200 caracteres.';
        else if (!/^[a-zA-ZáéíóúÁÉÍÓÚàèìòùÀÈÌÒÙñÑüÜ\s]+$/.test(v)) msg = 'Solo se permiten letras y espacios.';
        return promoErr(nombreInput, errNombre, msg, iconNombre);
    }

    let nombreTimer = null;
    async function validarNombreDuplicadoPromo() {
        if (!nombreInput || !validarUrl) return true;
        const v = nombreInput.value.trim();
        if (!v || v.length < 2) return true;

        if (nombreTimer) clearTimeout(nombreTimer);
        nombreTimer = setTimeout(async () => {
            try {
                const promocionId = form.dataset.promocionId || '';
                const url = new URL(validarUrl, window.location.origin);
                url.searchParams.set('nombre', v);
                if (promocionId) url.searchParams.set('promocion_id', promocionId);
                const response = await fetch(url.toString(), { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
                const data = await response.json().catch(() => ({}));
                if (!data.valid) {
                    nombreInput.dataset.nombreDuplicado = '1';
                    promoErr(nombreInput, errNombre, data.message || 'Ya existe una promocion con este nombre.', iconNombre);
                } else {
                    delete nombreInput.dataset.nombreDuplicado;
                    validarNombrePromo();
                }
            } catch (error) {
                // no bloquear por red
            }
        }, 250);
    }

    function validarDescuentoPromo() {
        if (!descInput || !errDesc) return true;
        const raw = descInput.value.trim();
        const val = parseFloat(raw);
        let msg = '';
        if (!raw) msg = 'El descuento es obligatorio.';
        else if (isNaN(val)) msg = 'Ingresa un número válido.';
        else if (val < 1) msg = 'El descuento mínimo es 1%.';
        else if (val > 100) msg = 'El descuento no puede superar el 100%.';
        return promoErr(descInput, errDesc, msg, iconDesc);
    }

    function validarFechasPromo() {
        if (!inicioInput || !finInput || !errInicio || !errFin) return true;
        const minDate = promoMinDate();
        const maxInicio = promoMaxInicio();
        const maxFin = promoMaxInicio();
        let ok = true;

        if (!inicioInput.value) {
            ok = promoErr(inicioInput, errInicio, 'La fecha de inicio es obligatoria.');
        } else if (inicioInput.value < minDate || inicioInput.value > maxInicio) {
            ok = promoErr(inicioInput, errInicio, 'La fecha de inicio debe estar dentro del ultimo año y no superar un año hacia el futuro.');
        } else {
            promoErr(inicioInput, errInicio, '');
        }

        finInput.min = inicioInput.value || minDate;

        if (!finInput.value) {
            ok = promoErr(finInput, errFin, 'La fecha de fin es obligatoria.') && ok;
        } else if (inicioInput.value && finInput.value < inicioInput.value) {
            ok = promoErr(finInput, errFin, 'La fecha de fin debe ser igual o posterior a la de inicio.') && ok;
        } else if (finInput.value < minDate || finInput.value > maxFin) {
            ok = promoErr(finInput, errFin, 'La fecha de fin debe estar dentro del ultimo año y no superar un año hacia el futuro.') && ok;
        } else {
            promoErr(finInput, errFin, '');
        }

        return ok;
    }

    function syncImagePreview(file) {
        if (!preview || !dropzone) return;
        if (!file) {
            preview.src = '';
            preview.classList.add('d-none');
            dropzone.classList.remove('has-image');
            return;
        }
        const reader = new FileReader();
        reader.onload = (e) => {
            preview.src = e.target.result;
            preview.classList.remove('d-none');
            dropzone.classList.add('has-image');
        };
        reader.readAsDataURL(file);
    }

    if (fileInput && preview) {
        fileInput.addEventListener('change', function () {
            if (this.files && this.files[0]) syncImagePreview(this.files[0]);
        });
    }

    if (dropzone) {
        dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('dragover'); });
        dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
        dropzone.addEventListener('drop', () => dropzone.classList.remove('dragover'));
    }

    if (descripcion && charDesc) {
        promoContador(descripcion, charDesc, 500);
        descripcion.addEventListener('input', () => promoContador(descripcion, charDesc, 500));
    }

    if (nombreInput) {
        nombreInput.addEventListener('input', () => {
            validarNombrePromo();
            validarNombreDuplicadoPromo();
        });
        nombreInput.addEventListener('blur', () => {
            validarNombrePromo();
            validarNombreDuplicadoPromo();
        });
    }
    if (descInput) {
        descInput.addEventListener('input', validarDescuentoPromo);
        descInput.addEventListener('blur', validarDescuentoPromo);
    }
    if (inicioInput) inicioInput.addEventListener('change', validarFechasPromo);
    if (finInput) finInput.addEventListener('change', validarFechasPromo);

    if (removeImageBtn) {
        removeImageBtn.addEventListener('click', function (e) {
            e.preventDefault();
            const chkClear = form.querySelector('#edit_imagen_clear');
            const infoClear = form.querySelector('#edit_info_clear');
            const prev = form.querySelector('#previewPromoEdit');
            if (!chkClear) return;

            chkClear.checked = !chkClear.checked;
            if (chkClear.checked) {
                infoClear?.classList.remove('d-none');
                if (prev) prev.style.filter = 'grayscale(1) opacity(0.5)';
                this.innerHTML = '<i class="bi bi-arrow-counterclockwise"></i> Restaurar';
                this.classList.replace('btn-danger', 'btn-warning');
            } else {
                infoClear?.classList.add('d-none');
                if (prev) prev.style.filter = 'none';
                this.innerHTML = '<i class="bi bi-trash3"></i> Eliminar';
                this.classList.replace('btn-warning', 'btn-danger');
            }
        });
    }

    form.addEventListener('submit', function (e) {
        let ok = true;
        if (nombreInput && !validarNombrePromo()) ok = false;
        if (descInput && !validarDescuentoPromo()) ok = false;
        if (inicioInput && finInput && !validarFechasPromo()) ok = false;
        if (!ok) e.preventDefault();
    });
}

function initPromoAlerts() {
    const source = document.querySelector('[data-promo-messages]');
    let messages = [];

    if (source) {
        try {
            messages = JSON.parse(source.dataset.promoMessages || '[]');
        } catch (error) {
            messages = [];
        }
    }

    if (messages.length) {
        messages.forEach(m => {
            const tag  = Object.keys(PROMO_TAGS_MAP).find(k => m.tags.includes(k)) || 'info';
            const opts = PROMO_TAGS_MAP[tag];
            Swal.fire({
                icon: opts.icon,
                title: tag === 'success' ? 'Éxito' : (tag === 'error' ? 'Error' : 'Información'),
                text: m.text,
                confirmButtonColor: '#3a2a24',
                timer: 3000,
                timerProgressBar: true
            });
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initPromoAlerts();

    const CSRF = () => document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

    initPromoFilterMenu();

    document.querySelectorAll('form[data-promo-form]').forEach((form) => {
        initPromoForm(form);
    });

    document.addEventListener('change', async function (e) {
        const input = e.target.closest('.promo-switch input');
        if (!input) return;

        const url = input.dataset.toggleUrl;
        const nombre = input.dataset.nombre || 'la promoción';
        if (!url) {
            input.checked = !input.checked;
            return;
        }

        input.disabled = true;

        try {
            const response = await fetch(url, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'X-CSRFToken': CSRF(),
                    'X-Requested-With': 'XMLHttpRequest',
                },
            });

            const data = await response.json().catch(() => ({}));

            if (!response.ok || !data.ok) {
                throw new Error(data.message || data.mensaje || 'No se pudo cambiar el estado.');
            }

            const activa = !!data.activa;
            const row = input.closest('tr');

            if (row) {
                const badge = row.querySelector('.promo-badge-active, .promo-badge-inactive');
                if (badge) {
                    badge.className = activa ? 'promo-badge-active' : 'promo-badge-inactive';
                    badge.textContent = activa ? 'Activa' : 'Inactiva';
                }

                const displayInput = row.querySelector('.promo-switch input');
                if (displayInput) {
                    displayInput.checked = activa;
                    displayInput.dataset.toggleUrl = url;
                }
            }

            if (typeof Swal !== 'undefined' && Swal.fire) {
                await Swal.fire({
                    icon: 'success',
                    title: 'Estado actualizado',
                    text: activa
                        ? `${nombre} quedó activa correctamente.`
                        : `${nombre} quedó inactiva correctamente.`,
                    confirmButtonColor: '#3a2a24',
                    confirmButtonText: 'OK',
                });
            }
        } catch (error) {
            input.checked = !input.checked;
            if (typeof Swal !== 'undefined' && Swal.fire) {
                await Swal.fire({
                    icon: 'error',
                    title: 'No se pudo cambiar el estado',
                    text: error.message || 'Intenta nuevamente.',
                    confirmButtonColor: '#3a2a24',
                    confirmButtonText: 'OK',
                });
            } else {
                alert(error.message || 'No se pudo cambiar el estado');
            }
        } finally {
            input.disabled = false;
        }
    });

    /* ── Función maestra para rellenar el modal ── */
    function fillEditModal(btn) {
        if (!btn) return;

        const form = document.getElementById('formEditar');
        if (form) {
            form.action = btn.dataset.editUrl || '';
            form.dataset.promocionId = btn.dataset.pk || '';
        }

        const setVal = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.value = val || '';
        };

        setVal('edit_nombre', btn.dataset.nombre);
        setVal('edit_etiqueta', btn.dataset.etiqueta);
        setVal('edit_descripcion', btn.dataset.descripcion);

        const descInput = document.getElementById('edit_descuento');
        if (descInput) {
            const raw = (btn.dataset.descuento || '0').toString().replace(',', '.');
            descInput.value = parseFloat(raw) || 0;
        }

        setVal('edit_inicio', btn.dataset.inicio);
        setVal('edit_fin', btn.dataset.fin);

        const chkActiva = document.getElementById('edit_activa');
        if (chkActiva) chkActiva.checked = (btn.dataset.activa === 'true');

        // Imagen
        const preview = document.getElementById('previewPromoEdit');
        const dz = document.getElementById('dropzonePromoEdit');
        const imgUrl = btn.dataset.imagenUrl;

        if (imgUrl && preview) {
            preview.src = imgUrl;
            preview.classList.remove('d-none');
            preview.style.filter = 'none';
            if (dz) dz.classList.add('has-image');
        } else if (preview) {
            preview.src = '';
            preview.classList.add('d-none');
            if (dz) dz.classList.remove('has-image');
        }

        // Reset campos de imagen
        const fileIn = document.getElementById('edit_imagen');
        if (fileIn) fileIn.value = '';
        const chkClear = document.getElementById('edit_imagen_clear');
        if (chkClear) chkClear.checked = false;
        const infoClear = document.getElementById('edit_info_clear');
        if (infoClear) infoClear.classList.add('d-none');
    }

    /* ── Listener Global para Clics (Delegación) ── */
    document.addEventListener('click', function(e) {
        const action = e.target.closest('[data-promo-action]');
        if (action && action.dataset.promoAction === 'pick-edit-image') {
            document.getElementById('edit_imagen')?.click();
            return;
        }

        // Botón Editar
        const btnEdit = e.target.closest('.btn-edit');
        if (btnEdit) {
            fillEditModal(btnEdit);
            
            // Forzar apertura si Bootstrap falla
            const modalEl = document.getElementById('modalEditar');
            if (modalEl) {
                const modalObj = bootstrap.Modal.getOrCreateInstance(modalEl);
                modalObj.show();
            }
            return;
        }

        // Botón Detalle
        const btnDet = e.target.closest('.btn-detalle-promo');
        if (btnDet) {
            window.__promoLastDetailButton = btnDet;
            const setDet = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val || ''; };
            setDet('promoDetNombre', btnDet.dataset.nombre);
            setDet('promoDetDescuento', (btnDet.dataset.descuento || '0') + '%');
            setDet('promoDetInicio', btnDet.dataset.inicio);
            setDet('promoDetFin', btnDet.dataset.fin);
            setDet('promoDetCreado', btnDet.dataset.creado);
            setDet('promoDetModificado', btnDet.dataset.modificado);
            setDet('promoDetDesc', btnDet.dataset.descripcion || '—');
            
            const et = document.getElementById('promoDetEtiqueta');
            if (et) { et.textContent = btnDet.dataset.etiqueta; et.className = 'badge bg-secondary rounded-pill px-3'; }

            const img = document.getElementById('promoDetImg');
            const ph = document.getElementById('promoDetImgPh');
            if (btnDet.dataset.imagenUrl && img) {
                img.src = btnDet.dataset.imagenUrl;
                img.classList.remove('d-none');
                img.style.display = 'block';
                if (ph) ph.style.display = 'none';
            } else if (img) {
                img.classList.add('d-none');
                img.style.display = 'none';
                if (ph) ph.style.display = 'block';
            }

            const mDet = document.getElementById('modalDetallePromo');
            if (mDet) bootstrap.Modal.getOrCreateInstance(mDet).show();
            return;
        }

        // Botón Eliminar
        const btnDel = e.target.closest('.btn-eliminar-promo');
        if (btnDel) {
            Swal.fire({
                title: '¿Eliminar promoción?',
                text: `¿Seguro que deseas eliminar "${btnDel.dataset.nombre}"?`,
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#dc3545',
                confirmButtonText: 'Sí, eliminar',
                cancelButtonText: 'Cancelar'
            }).then(res => {
                if (res.isConfirmed) {
                    const f = document.getElementById('formEliminarPromo');
                    if (f) { f.action = btnDel.dataset.url; f.submit(); }
                }
            });
        }

        const btnDetalleEditar = e.target.closest('#btnDetalleEditar');
        if (btnDetalleEditar) {
            const btnEdit = window.__promoLastDetailButton || document.querySelector('.btn-edit');
            if (btnEdit) {
                fillEditModal(btnEdit);
                const modalEl = document.getElementById('modalEditar');
                if (modalEl) {
                    bootstrap.Modal.getOrCreateInstance(modalEl).show();
                }
            }
        }
    });

    // Lógica específica para el botón de eliminar imagen dentro del modal
    const btnRemoveImg = document.getElementById('btnRemoveImageEdit');
    btnRemoveImg?.addEventListener('click', function(e) {
        e.preventDefault();
        const chkClear = document.getElementById('edit_imagen_clear');
        const infoClear = document.getElementById('edit_info_clear');
        const preview = document.getElementById('previewPromoEdit');
        if (!chkClear) return;

        chkClear.checked = !chkClear.checked;
        if (chkClear.checked) {
            infoClear?.classList.remove('d-none');
            if (preview) preview.style.filter = 'grayscale(1) opacity(0.5)';
            this.innerHTML = '<i class="bi bi-arrow-counterclockwise"></i> Restaurar';
            this.classList.replace('btn-danger', 'btn-warning');
        } else {
            infoClear?.classList.add('d-none');
            if (preview) preview.style.filter = 'none';
            this.innerHTML = '<i class="bi bi-trash3"></i> Eliminar';
            this.classList.replace('btn-warning', 'btn-danger');
        }
    });

    const btnEliminarPromo = document.getElementById('btnEliminarPromo');
    if (btnEliminarPromo) {
        btnEliminarPromo.addEventListener('click', function () {
            const form = document.getElementById('formEliminarPromo');
            const promoNombre = this.dataset.nombre || '';
            Swal.fire({
                title: '¿Eliminar promoción?',
                html: `¿Seguro que deseas eliminar <strong>${promoNombre}</strong>?<br><small class="text-muted">Esta acción no se puede deshacer.</small>`,
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#dc3545',
                cancelButtonColor: '#6c757d',
                confirmButtonText: '<i class="bi bi-trash3"></i> Sí, eliminar',
                cancelButtonText: 'Cancelar',
                reverseButtons: true,
            }).then((result) => {
                if (result.isConfirmed && form) {
                    form.submit();
                }
            });
        });
    }
});
