const root = document;

function toast(msg, type = 'success') {
  const el = root.getElementById('notificacionToast');
  if (!el || !window.bootstrap) return alert(msg);
  const map = {
    success: { color: '#198754', icon: 'bi-check-circle-fill', title: 'Exito' },
    error: { color: '#dc3545', icon: 'bi-x-circle-fill', title: 'Error' },
    warning: { color: '#ffc107', icon: 'bi-exclamation-triangle-fill', title: 'Advertencia' },
    info: { color: '#0dcaf0', icon: 'bi-info-circle-fill', title: 'Informacion' },
  };
  const cfg = map[type] || map.info;
  const header = el.querySelector('.toast-header');
  const icon = root.getElementById('toastIcon');
  const title = root.getElementById('toastTitle');
  const body = root.getElementById('toastMessage');
  if (header) header.style.backgroundColor = cfg.color;
  if (icon) icon.className = `${cfg.icon} me-2`;
  if (title) title.textContent = cfg.title;
  if (body) body.textContent = msg;
  new bootstrap.Toast(el).show();
}

function esc(v) {
  return String(v ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function getField(form, name) { return form ? form.querySelector(`[name="${name}"]`) : null; }
function selectText(el) { if (!el) return '—'; if (el.tagName !== 'SELECT') return (el.value || '—').trim() || '—'; const opt = el.selectedOptions && el.selectedOptions[0]; return opt && opt.value ? (opt.text || '—').trim() || '—' : '—'; }
function splitCliente(texto) { const t = String(texto || '').trim(); const p = t.lastIndexOf(' - '); return p >= 0 ? { nombre: t.slice(0, p).trim(), documento: t.slice(p + 3).trim() } : { nombre: t, documento: '' }; }
function show(el, on) { if (el) el.classList.toggle('show', !!on); }
function vis(el, on) { if (el) el.style.display = on ? 'inline-block' : 'none'; }

function generarHTMLDocumento(datos) {
  const css = `*{box-sizing:border-box}body{font-family:Arial,sans-serif;font-size:11pt;color:#222;padding:20px}.header{display:flex;align-items:center;gap:16px;border-bottom:3px solid #634c40;padding-bottom:12px;margin-bottom:18px}.header-text h1{font-size:13pt;color:#634c40}.header-text p,.fecha-box{font-size:9pt;color:#666}.fecha-box{text-align:right;margin-bottom:10px}.seccion{margin-bottom:14px}.seccion-titulo{background:#634c40;color:#fff;padding:5px 10px;font-size:10pt;font-weight:bold;border-radius:3px;margin-bottom:8px}.fila{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:5px}.campo{flex:1;min-width:170px}.campo-label{font-size:8pt;color:#634c40;font-weight:bold;text-transform:uppercase}.campo-valor{font-size:10pt;border-bottom:1px solid #ccc;padding:2px 4px;min-height:20px}.campo-valor.largo{border:1px solid #ccc;padding:4px;min-height:36px;border-radius:3px;margin-top:2px}.procesos-grid{display:flex;flex-wrap:wrap;gap:6px}.proceso-item{border:1px solid #ccc;border-radius:3px;padding:3px 8px;font-size:9.5pt}.proceso-si{background:#f0e8e4;border-color:#634c40;color:#634c40;font-weight:bold}.proceso-no{color:#aaa}.firma-seccion{margin-top:30px;border-top:2px solid #634c40;padding-top:20px;display:flex;justify-content:space-between}.firma-box{text-align:center;flex:1;padding:0 20px}.firma-linea{border-top:1px solid #333;margin-top:50px;margin-bottom:5px}.firma-texto{font-size:9pt;color:#555}.consent-box{background:#f9f4f2;border:1px solid #d4b8ac;border-radius:4px;padding:10px 14px;margin-bottom:14px;font-size:9pt;color:#444}.consent-box strong{color:#634c40}@media print{@page{margin:15mm;size:A4}body{padding:0}}`;
  const procesos = [
    ['Tintura', datos.tintura], ['Decoloracion', datos.decoloracion], ['Ondulados Perm', datos.ondulados],
    ['Extracciones', datos.extracciones], ['Alisados', datos.alisados], ['Super Aclarante', datos.superAclarante],
  ];
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Tratamiento de Alisado - ${esc(datos.clienteNombre)}</title><style>${css}</style></head><body>
  <div class="header"><div class="header-text"><h1>TRATAMIENTO DE DATOS - SERVICIO DE ALISADO</h1><p>Formulario de Gestion y Consentimiento Informado</p></div></div>
  <div class="fecha-box">Fecha de registro: <strong>${esc(datos.fecha)}</strong></div>
  <div class="seccion"><div class="seccion-titulo">Informacion del Cliente</div><div class="fila"><div class="campo"><div class="campo-label">Nombre completo</div><div class="campo-valor">${esc(datos.clienteNombre)}</div></div><div class="campo"><div class="campo-label">Numero de documento</div><div class="campo-valor">${esc(datos.clienteDocumento)}</div></div></div></div>
  <div class="seccion"><div class="seccion-titulo">Informacion del Servicio y Pago</div><div class="fila"><div class="campo"><div class="campo-label">Precio del Alisado</div><div class="campo-valor">$ ${esc(datos.precioAlisado)}</div></div><div class="campo"><div class="campo-label">Anticipo</div><div class="campo-valor">$ ${esc(datos.anticipo)}</div></div><div class="campo"><div class="campo-label">Saldo Pendiente</div><div class="campo-valor">$ ${esc(datos.saldo)}</div></div><div class="campo"><div class="campo-label">Medio de Pago</div><div class="campo-valor">${esc(datos.medioPago)}</div></div><div class="campo"><div class="campo-label">Oferta especial</div><div class="campo-valor">${esc(datos.esOferta)}${datos.esOferta === 'Si' ? ' - ' + esc(datos.descripOferta) : ''}</div></div></div></div>
  <div class="seccion"><div class="seccion-titulo">Informacion del Procedimiento</div><div class="fila"><div class="campo"><div class="campo-label">Realizado por</div><div class="campo-valor">${esc(datos.realizadoPor)}</div></div><div class="campo"><div class="campo-label">Porcentaje de Alisado</div><div class="campo-valor">${esc(datos.porcentaje)}</div></div><div class="campo"><div class="campo-label">Requiere Resellado</div><div class="campo-valor">${esc(datos.resellado)}</div></div></div><div class="campo"><div class="campo-label">Tipo de Alisado</div><div class="campo-valor largo">${esc(datos.tipoAlisado)}</div></div></div>
  <div class="seccion"><div class="seccion-titulo">Caracteristicas del Cabello</div><div class="fila"><div class="campo"><div class="campo-label">Porosidad</div><div class="campo-valor">${esc(datos.porosidad)}</div></div><div class="campo"><div class="campo-label">Textura</div><div class="campo-valor">${esc(datos.textura)}</div></div><div class="campo"><div class="campo-label">Forma Natural</div><div class="campo-valor">${esc(datos.formaNatural)}</div></div><div class="campo"><div class="campo-label">Elasticidad</div><div class="campo-valor">${esc(datos.elasticidad)}</div></div></div><div class="fila"><div class="campo"><div class="campo-label">Longitud</div><div class="campo-valor">${esc(datos.longitud)}</div></div><div class="campo"><div class="campo-label">Densidad</div><div class="campo-valor">${esc(datos.densidad)}</div></div><div class="campo"><div class="campo-label">Piel Cabelludo</div><div class="campo-valor">${esc(datos.pielCabelludo)}</div></div><div class="campo"><div class="campo-label">Alopecia</div><div class="campo-valor">${esc(datos.alopecia)}</div></div><div class="campo"><div class="campo-label">Caida de Cabello</div><div class="campo-valor">${esc(datos.caida)}</div></div><div class="campo"><div class="campo-label">Caspa</div><div class="campo-valor">${esc(datos.caspa)}</div></div></div></div>
  <div class="seccion"><div class="seccion-titulo">Estado de Salud y Condiciones Especiales</div><div class="fila"><div class="campo"><div class="campo-label">Lactante</div><div class="campo-valor">${esc(datos.lactante)}</div></div><div class="campo"><div class="campo-label">Gestante</div><div class="campo-valor">${esc(datos.gestante)}</div></div><div class="campo"><div class="campo-label">Tiroides</div><div class="campo-valor">${esc(datos.tiroides)}${datos.tiroides === 'Si' ? ' - ' + esc(datos.medTiroides) : ''}</div></div><div class="campo"><div class="campo-label">Despunte hoy</div><div class="campo-valor">${esc(datos.despunte)}</div></div></div></div>
  <div class="seccion"><div class="seccion-titulo">Procesos Quimicos Previos</div><div class="procesos-grid">${procesos.map(([l,v]) => `<div class="proceso-item ${v === 'Si' ? 'proceso-si' : 'proceso-no'}">${v === 'Si' ? '✓' : '○'} ${esc(l)}</div>`).join('')}</div>${datos.otrosProcesos && datos.otrosProcesos !== '—' ? `<div style="margin-top:6px"><div class="campo-label">Otro:</div><div class="campo-valor">${esc(datos.otrosProcesos)}</div></div>` : ''}</div>
  <div class="seccion"><div class="seccion-titulo">Habitos y Cuidados</div><div class="fila"><div class="campo"><div class="campo-label">Tiene secador</div><div class="campo-valor">${esc(datos.secador)}</div></div><div class="campo"><div class="campo-label">Usa casco</div><div class="campo-valor">${esc(datos.usaCasco)}</div></div><div class="campo"><div class="campo-label">Bana con agua caliente</div><div class="campo-valor">${esc(datos.aguaCaliente)}</div></div><div class="campo"><div class="campo-label">Refuerzo 15 dias</div><div class="campo-valor">${esc(datos.refuerzo15)}</div></div><div class="campo"><div class="campo-label">Realiza ejercicio</div><div class="campo-valor">${esc(datos.ejercicio)}${datos.ejercicio === 'Si' ? ' - ' + esc(datos.frecEjercicio) : ''}</div></div></div><div class="campo"><div class="campo-label">Cada cuanto recoge el cabello</div><div class="campo-valor largo">${esc(datos.frecRecoge)}</div></div><div class="campo" style="margin-top:6px"><div class="campo-label">Productos capilares</div><div class="campo-valor largo">${esc(datos.productos)}</div></div></div>
  <div class="seccion"><div class="seccion-titulo">Recomendaciones y Anotaciones</div><div class="campo"><div class="campo-valor largo">${esc(datos.recomendaciones)}</div></div></div>
  <div class="consent-box"><strong>Consentimiento Informado:</strong> El/La cliente declara haber leido y comprendido todos los terminos y condiciones del tratamiento de alisado.</div>
  <div class="firma-seccion"><div class="firma-box"><div class="firma-linea"></div><div class="firma-texto"><strong>${esc(datos.clienteNombre)}</strong></div><div class="firma-texto">Doc: ${esc(datos.clienteDocumento)}</div><div class="firma-texto">Firma del Cliente</div></div><div class="firma-box"><div class="firma-linea"></div><div class="firma-texto"><strong>${esc(datos.realizadoPor)}</strong></div><div class="firma-texto">Responsable del Procedimiento</div></div></div>
  </body></html>`;
}

function datosFormulario(form) {
  return {
    clienteNombre: form.querySelector('#clienteNombreImpresion')?.value || '—',
    clienteDocumento: form.querySelector('#clienteDocumentoImpresion')?.value || '—',
    fecha: new Date().toLocaleDateString('es-CO', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' }),
    precioAlisado: getField(form, 'precio_alisado')?.value || '—',
    anticipo: getField(form, 'anticipo_cliente')?.value || '—',
    saldo: getField(form, 'saldo_pendiente')?.value || '—',
    medioPago: selectText(getField(form, 'medio_pago')),
    esOferta: selectText(getField(form, 'es_oferta_especial')),
    descripOferta: getField(form, 'descripcion_oferta')?.value || '—',
    realizadoPor: selectText(getField(form, 'procedimiento_realizado_por')),
    tipoAlisado: selectText(getField(form, 'tipo_alisado')),
    resellado: selectText(getField(form, 'requiere_resellado')),
    porcentaje: getField(form, 'porcentaje_alisado')?.value ? `${getField(form, 'porcentaje_alisado').value}%` : '—',
    porosidad: selectText(getField(form, 'porosidad')),
    textura: selectText(getField(form, 'textura')),
    formaNatural: selectText(getField(form, 'forma_natural')),
    elasticidad: selectText(getField(form, 'elasticidad')),
    longitud: selectText(getField(form, 'longitud')),
    densidad: selectText(getField(form, 'densidad')),
    pielCabelludo: selectText(getField(form, 'piel_cabelludo')),
    alopecia: selectText(getField(form, 'alopecia')),
    caida: selectText(getField(form, 'caida_cabello')),
    caspa: selectText(getField(form, 'caspa')),
    lactante: getField(form, 'lactante')?.value === 'si' ? 'Si' : 'No',
    gestante: getField(form, 'gestante')?.value === 'si' ? 'Si' : 'No',
    tiroides: getField(form, 'sufre_tiroides')?.value === 'si' ? 'Si' : 'No',
    medTiroides: getField(form, 'medicamento_tiroides')?.value || '—',
    despunte: getField(form, 'despunte_hoy')?.value === 'si' ? 'Si' : 'No',
    tintura: getField(form, 'procesos_tintura')?.checked ? 'Si' : 'No',
    decoloracion: getField(form, 'procesos_decoloracion')?.checked ? 'Si' : 'No',
    ondulados: getField(form, 'procesos_ondulados')?.checked ? 'Si' : 'No',
    extracciones: getField(form, 'procesos_extracciones')?.checked ? 'Si' : 'No',
    alisados: getField(form, 'procesos_alisados')?.checked ? 'Si' : 'No',
    superAclarante: getField(form, 'procesos_super_aclarante')?.checked ? 'Si' : 'No',
    otrosProcesos: getField(form, 'procesos_otro')?.value || '—',
    secador: getField(form, 'cuenta_con_secador')?.checked ? 'Si' : 'No',
    usaCasco: getField(form, 'usa_casco')?.checked ? 'Si' : 'No',
    aguaCaliente: getField(form, 'se_bana_agua_caliente')?.checked ? 'Si' : 'No',
    refuerzo15: getField(form, 'requiere_refuerzo_15dias')?.checked ? 'Si' : 'No',
    ejercicio: getField(form, 'realiza_ejercicio')?.value === 'si' ? 'Si' : 'No',
    frecEjercicio: getField(form, 'frecuencia_ejercicio')?.value || '—',
    frecRecoge: getField(form, 'frecuencia_recoge_cabello')?.value || '—',
    productos: getField(form, 'productos_capilares')?.value || '—',
    recomendaciones: getField(form, 'recomendaciones_post_cuidados')?.value || '—',
  };
}

function initGestionForm() {
  const form = root.getElementById('gestionAlisadoForm');
  if (!form || form.dataset.gestionWired === '1') return;
  form.dataset.gestionWired = '1';

  const selectCliente = root.getElementById('selectCliente');
  const infoCliente = root.getElementById('infoClienteConsentimiento');
  const btnSiguiente = root.getElementById('btnSiguiente');
  const btnAnterior = root.getElementById('btnAnterior');
  const btnGuardar = root.getElementById('btnGuardar');
  const modalConsentimientoEl = root.getElementById('modalConsentimiento');
  const checkboxAceptacion = root.getElementById('checkboxAceptacion');
  const btnConfirmar = root.getElementById('btnConfirmarConsentimiento');
  const btnCerrar = root.getElementById('btnCerrarModal');
  const inputFirma = root.getElementById('id_firma_consentimiento');
  const errorFirma = root.getElementById('errorFirma');
  const wrapperCheck = root.getElementById('wrapperCheckboxAceptacion');
  const msgCheck = root.getElementById('msgCheckboxError');
  const btnImprimirPDF = root.getElementById('btnImprimirPDF');
  const btnImprimirWord = root.getElementById('btnImprimirWord');
  const btnReporte = root.getElementById('btnReportePdfPreview');
  const modalCliente = root.getElementById('modalCrearCliente');
  const formCliente = root.getElementById('formCrearCliente');
  const btnGuardarCliente = root.getElementById('btnGuardarClienteModal');
  const urlUltima = form.dataset.ultimaGestionUrl || '';
  const esEdicion = form.dataset.esEdicion === '1';

  let currentStep = 1;

  function setStep(step) {
    root.querySelectorAll('.form-step').forEach((el) => el.classList.remove('active'));
    const current = root.getElementById(`step${step}`);
    if (current) current.classList.add('active');
    root.querySelectorAll('.step-item').forEach((item) => {
      const n = parseInt(item.dataset.step || '0', 10);
      item.classList.toggle('active', n === step);
      item.classList.toggle('completed', n < step);
    });
    vis(btnAnterior, step > 1);
    vis(btnSiguiente, step < 2);
    vis(btnGuardar, step === 2);
  }

  function selectedCliente() {
    if (!selectCliente || !selectCliente.value) return null;
    const opt = selectCliente.selectedOptions && selectCliente.selectedOptions[0];
    if (!opt) return null;
    const parsed = splitCliente(opt.text || '');
    return {
      nombre: (opt.getAttribute('data-nombre') || parsed.nombre || '').trim() || '—',
      documento: (opt.getAttribute('data-documento') || parsed.documento || '').trim() || '—',
    };
  }

  function updateInfoCliente() {
    const c = selectedCliente();
    if (!c) {
      if (infoCliente) infoCliente.textContent = 'Seleccione un cliente en el formulario';
      return;
    }
    if (infoCliente) infoCliente.innerHTML = `<strong>Nombre:</strong> ${esc(c.nombre)}<br><strong>Documento:</strong> ${esc(c.documento)}`;
    const n = root.getElementById('clienteNombreImpresion'); if (n) n.value = c.nombre;
    const d = root.getElementById('clienteDocumentoImpresion'); if (d) d.value = c.documento;
  }

  function toggleSections() {
    const oferta = getField(form, 'es_oferta_especial');
    show(root.getElementById('descripcion_oferta_container'), oferta && oferta.value === 'si');
    show(root.getElementById('promocion_oferta_container'), oferta && oferta.value === 'si');
    show(root.getElementById('medicamento_tiroides_container'), getField(form, 'sufre_tiroides')?.value === 'si');
    show(root.getElementById('frecuencia_ejercicio_container'), getField(form, 'realiza_ejercicio')?.value === 'si');
  }

  function calculateSaldo() {
    const precio = parseFloat(getField(form, 'precio_alisado')?.value || '0') || 0;
    const anticipo = parseFloat(getField(form, 'anticipo_cliente')?.value || '0') || 0;
    const saldo = getField(form, 'saldo_pendiente');
    if (saldo) saldo.value = String(Math.max(0, precio - anticipo));
  }

  function updateImpresion() {
    const estado = datosFormulario(form);
    form._gestionEstado = estado;
  }

  async function loadHistorial() {
    if (!selectCliente || !selectCliente.value || esEdicion || !urlUltima) return;
    try {
      const res = await fetch(`${urlUltima}?cliente=${encodeURIComponent(selectCliente.value)}`, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
      const data = await res.json();
      if (!data || !data.success || !data.tiene_historial || !data.datos) return;
      Object.entries(data.datos).forEach(([k, v]) => {
        const field = getField(form, k);
        if (!field) return;
        if (field.type === 'checkbox') field.checked = !!v;
        else if (field.tagName === 'SELECT') field.value = String(v ?? '');
        else field.value = v ?? '';
      });
      updateInfoCliente(); toggleSections(); calculateSaldo(); updateImpresion();
    } catch (e) { console.warn(e); }
  }

  function validateStep(step) {
    const stepEl = root.getElementById(`step${step}`);
    if (!stepEl) return true;
    let ok = true;
    let first = null;
    stepEl.querySelectorAll('input[required], select[required], textarea[required]').forEach((field) => {
      const hidden = field.closest('.conditional-field') && !field.closest('.conditional-field').classList.contains('show');
      if (field.disabled || hidden || field.offsetParent === null) return;
      if (!String(field.value || '').trim() || (field.tagName === 'SELECT' && (field.value === '' || field.value === 'None'))) {
        ok = false; field.classList.add('is-invalid'); if (!first) first = field;
      }
    });
    if (!ok && first) first.focus();
    return ok;
  }

  function validarConsentimiento() {
    const c = !!selectedCliente();
    const a = !!checkboxAceptacion?.checked;
    const f = !!(inputFirma && inputFirma.files && inputFirma.files.length > 0);
    if (errorFirma) errorFirma.style.display = (a && !f) ? 'block' : 'none';
    if (btnConfirmar) btnConfirmar.disabled = !(c && a && f);
  }

  function shakeCheckbox() {
    if (!wrapperCheck || !msgCheck) return;
    wrapperCheck.classList.add('alerta-tc');
    msgCheck.classList.add('visible');
  }

  function wireClienteModal() {
    if (!modalCliente || !formCliente || !btnGuardarCliente) return;
    const inputs = modalCliente.querySelectorAll('input, select');
    const updateBtn = () => {
      let ok = true;
      inputs.forEach((i) => { if (i.type !== 'hidden' && !String(i.value || '').trim()) ok = false; });
      btnGuardarCliente.disabled = !ok;
    };
    inputs.forEach((i) => i.addEventListener('input', updateBtn));
    modalCliente.addEventListener('hidden.bs.modal', () => { formCliente.reset(); updateBtn(); });
    updateBtn();
  }

  function initConsentModal() {
    if (!modalConsentimientoEl || !checkboxAceptacion || !btnConfirmar) return;
    const modal = bootstrap.Modal.getOrCreateInstance(modalConsentimientoEl);
    btnCerrar?.addEventListener('click', () => modal.hide());
    checkboxAceptacion.addEventListener('change', validarConsentimiento);
    inputFirma?.addEventListener('change', validarConsentimiento);
    selectCliente?.addEventListener('change', validarConsentimiento);
    btnConfirmar.addEventListener('click', () => {
      const c = selectedCliente();
      if (!c) return toast('Seleccione un cliente', 'warning');
      if (!checkboxAceptacion.checked) return shakeCheckbox();
      if (!(inputFirma && inputFirma.files && inputFirma.files.length > 0)) { if (errorFirma) errorFirma.style.display = 'block'; return; }
      ['consentimiento_nombre','consentimiento_cedula','consentimiento_fecha','consentimiento_aceptado'].forEach((name) => { form.querySelectorAll(`input[name="${name}"]`).forEach((n) => n.remove()); });
      [['consentimiento_nombre', c.nombre], ['consentimiento_cedula', c.documento], ['consentimiento_fecha', new Date().toLocaleDateString('es-CO', { year:'numeric', month:'long', day:'numeric', hour:'2-digit', minute:'2-digit' })], ['consentimiento_aceptado', 'true']].forEach(([name, value]) => { const i = document.createElement('input'); i.type = 'hidden'; i.name = name; i.value = value; form.appendChild(i); });
      modal.hide(); form.submit();
    });
    validarConsentimiento();
  }

  selectCliente?.addEventListener('change', async () => { updateInfoCliente(); toggleSections(); calculateSaldo(); updateImpresion(); await loadHistorial(); });
  getField(form, 'precio_alisado')?.addEventListener('input', () => { calculateSaldo(); updateImpresion(); });
  getField(form, 'anticipo_cliente')?.addEventListener('input', () => { calculateSaldo(); updateImpresion(); });
  getField(form, 'es_oferta_especial')?.addEventListener('change', () => { toggleSections(); updateImpresion(); });
  getField(form, 'sufre_tiroides')?.addEventListener('change', toggleSections);
  getField(form, 'realiza_ejercicio')?.addEventListener('change', toggleSections);
  getField(form, 'porcentaje_alisado')?.addEventListener('input', function () { const v = parseInt(this.value || '0', 10); if (!Number.isNaN(v)) this.value = Math.min(Math.max(v, 0), 100); updateImpresion(); });
  form.querySelectorAll('input, select, textarea').forEach((el) => { const ev = el.tagName === 'SELECT' ? 'change' : 'input'; el.addEventListener(ev, updateImpresion); });

  btnSiguiente?.addEventListener('click', () => { if (validateStep(currentStep) && currentStep < 2) { currentStep += 1; setStep(currentStep); } });
  btnAnterior?.addEventListener('click', () => { if (currentStep > 1) { currentStep -= 1; setStep(currentStep); } });
  btnGuardar?.addEventListener('click', (e) => { e.preventDefault(); if (!validateStep(currentStep)) return; if (!selectCliente?.value) return toast('Seleccione un cliente', 'warning'); checkboxAceptacion && (checkboxAceptacion.checked = false); validarConsentimiento(); updateInfoCliente(); modalConsentimientoEl && bootstrap.Modal.getOrCreateInstance(modalConsentimientoEl).show(); });

  btnImprimirPDF?.addEventListener('click', (e) => { e.preventDefault(); const html = generarHTMLDocumento(datosFormulario(form)); const w = window.open('data:text/html;charset=utf-8,' + encodeURIComponent(html), '_blank', 'width=860,height=720'); if (!w) return toast('Permite las ventanas emergentes e intenta de nuevo.', 'warning'); setTimeout(() => { try { w.print(); } catch {} }, 700); });
  btnImprimirWord?.addEventListener('click', (e) => { e.preventDefault(); const html = generarHTMLDocumento(datosFormulario(form)); const blob = new Blob(['\ufeff' + html], { type: 'application/msword;charset=utf-8' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `Alisado_${(selectedCliente()?.nombre || 'cliente').replace(/\s+/g, '_')}_${new Date().toISOString().slice(0,10)}.doc`; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url); toast('Documento Word descargado correctamente.', 'success'); });

  if (btnReporte) {
    btnReporte.addEventListener('click', function () {
      const base = this.dataset.previewBase || '';
      const formFiltros = root.getElementById('filtrosForm');
      if (!base || !formFiltros) return;
      const params = new URLSearchParams();
      ['buscar','forma_natural','porosidad','textura','estado_pago'].forEach((n) => {
        const el = formFiltros.querySelector(`[name="${n}"]`);
        params.set(n, el ? el.value : '');
      });
      this.dataset.previewUrl = `${base}?${params.toString()}`;
    }, true);
  }

  setStep(1);
  updateInfoCliente();
  toggleSections();
  calculateSaldo();
  updateImpresion();
  initConsentModal();
  wireClienteModal();
  if (selectCliente?.value && !esEdicion) loadHistorial();
}

document.addEventListener('DOMContentLoaded', function () {
  initGestionForm();
});
