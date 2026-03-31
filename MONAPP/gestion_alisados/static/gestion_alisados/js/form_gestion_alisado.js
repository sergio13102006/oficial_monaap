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

function setStepAlert(message, type = 'warning') {
  const el = root.getElementById('gestionStepAlert');
  if (!el) {
    toast(message, type);
    return;
  }

  el.classList.remove('d-none', 'alert-success', 'alert-danger', 'alert-warning', 'alert-info');
  const map = {
    success: 'alert-success',
    error: 'alert-danger',
    warning: 'alert-warning',
    info: 'alert-info',
  };
  el.classList.add(map[type] || 'alert-warning');
  el.innerHTML = `<i class="bi bi-exclamation-triangle-fill me-2"></i><span>${esc(message)}</span>`;
}

function clearStepAlert() {
  const el = root.getElementById('gestionStepAlert');
  if (!el) return;
  el.classList.add('d-none');
  el.classList.remove('alert-success', 'alert-danger', 'alert-warning', 'alert-info');
  el.innerHTML = '';
}

function notifyStepError() {
  setStepAlert('Completa la información antes de continuar.', 'warning');
}

function fieldDisplayName(field) {
  if (!field) return 'Campo';
  if (field.name === 'firma_consentimiento_data') return 'Firma del cliente';
  const id = field.id;
  if (id && window.CSS && typeof window.CSS.escape === 'function') {
    const label = document.querySelector(`label[for="${window.CSS.escape(id)}"]`);
    if (label) return (label.textContent || 'Campo').replace(/\*/g, '').trim();
  }
  if (id) {
    const fallbackLabel = document.querySelector(`label[for="${id}"]`);
    if (fallbackLabel) return (fallbackLabel.textContent || 'Campo').replace(/\*/g, '').trim();
  }
  return (field.getAttribute('aria-label') || field.name || 'Campo').trim();
}

function esc(v) {
  return String(v ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function getField(form, name) { return form ? form.querySelector(`[name="${name}"]`) : null; }
function selectText(el) { if (!el) return '—'; if (el.tagName !== 'SELECT') return (el.value || '—').trim() || '—'; const opt = el.selectedOptions && el.selectedOptions[0]; return opt && opt.value ? (opt.text || '—').trim() || '—' : '—'; }
function splitCliente(texto) { const t = String(texto || '').trim(); const p = t.lastIndexOf(' - '); return p >= 0 ? { nombre: t.slice(0, p).trim(), documento: t.slice(p + 3).trim() } : { nombre: t, documento: '' }; }
function moneyDigits(value) { return String(value ?? '').replace(/[^\d]/g, ''); }
function formatMoneyValue(value) {
  const digits = moneyDigits(value);
  if (!digits) return '';
  const normalized = digits.replace(/^0+(?=\d)/, '');
  return normalized.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}
function parseMoneyValue(field) { return parseInt(moneyDigits(field?.value || '0') || '0', 10) || 0; }
function formatMoneyField(field) {
  if (!field) return;
  const formatted = formatMoneyValue(field.value);
  field.value = formatted;
}
function calculateMoneySaldoForForm(formRef) {
  if (!formRef) return;
  const precio = parseMoneyValue(getField(formRef, 'precio_alisado'));
  const anticipo = parseMoneyValue(getField(formRef, 'anticipo_cliente'));
  const saldo = getField(formRef, 'saldo_pendiente');
  if (saldo) saldo.value = formatMoneyValue(Math.max(0, precio - anticipo));
}
function syncMoneyFields(formRef) {
  if (!formRef) return;
  [getField(formRef, 'precio_alisado'), getField(formRef, 'anticipo_cliente'), getField(formRef, 'saldo_pendiente')].forEach(formatMoneyField);
  calculateMoneySaldoForForm(formRef);
}
function wireMoneyField(field) {
  if (!field || field.dataset.moneyWired === '1') return;
  field.dataset.moneyWired = '1';
  const sync = () => {
    formatMoneyField(field);
    const formRef = field.closest('form');
    calculateMoneySaldoForForm(formRef);
    if (formRef && formRef._gestionUpdateImpresion) formRef._gestionUpdateImpresion();
  };
  ['input', 'keyup', 'change', 'paste', 'blur'].forEach((eventName) => {
    field.addEventListener(eventName, sync);
  });
  if (!field.readOnly) {
    field.addEventListener('focus', () => {
      if (moneyDigits(field.value) === '0') field.value = '';
    });
  }
}
window.gestionAlisadoMoneyInput = function gestionAlisadoMoneyInput(field) {
  if (!field) return;
  const formRef = field.closest('form');
  formatMoneyField(field);
  calculateMoneySaldoForForm(formRef);
  if (formRef && formRef._gestionUpdateImpresion) formRef._gestionUpdateImpresion();
};
window.gestionAlisadoMoneyFocus = function gestionAlisadoMoneyFocus(field) {
  if (!field) return;
  if (moneyDigits(field.value) === '0') field.value = '';
};
function show(el, on) { if (el) el.classList.toggle('show', !!on); }
  function vis(el, on) { if (el) el.style.display = on ? 'inline-block' : 'none'; }
  function setPcLauncherStatus(message, tone = 'info') {
    if (!tabletProcessStatus) return;
    tabletProcessStatus.textContent = message;
    tabletProcessStatus.dataset.tone = tone;
  }

  async function handleTabletStartProcess(event) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }

    const c = selectedCliente();
    if (!c) {
      setPcLauncherStatus('Selecciona un cliente para iniciar el proceso.', 'warning');
      toast('Selecciona un cliente para iniciar el proceso.', 'warning');
      return;
    }

    const startUrl = tabletStartProcess?.dataset.startUrl || buildTabletStartUrl(selectCliente?.value || '');
    if (!startUrl) {
      setPcLauncherStatus('No se pudo construir el enlace del proceso.', 'error');
      toast('No se pudo construir el enlace del proceso.', 'error');
      return;
    }

    if (tabletStartProcess) tabletStartProcess.disabled = true;
    setPcLauncherStatus(`Enviando proceso para ${c.nombre}...`, 'info');

    try {
      const res = await fetch(startUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
      const data = await res.json();
      if (!data || !data.success) throw new Error('bad response');
      if (tabletProcessStatus) {
        tabletProcessStatus.textContent = `Proceso enviado a la tablet para ${data.cliente?.nombre || c.nombre}. Mantén la pantalla de espera abierta.`;
        tabletProcessStatus.dataset.tone = 'success';
      }
      toast('Proceso enviado a la tablet.', 'success');
      updateTabletLink();
    } catch (err) {
      console.warn(err);
      setPcLauncherStatus('No se pudo enviar el proceso a la tablet.', 'error');
      toast('No se pudo enviar el proceso a la tablet.', 'error');
    } finally {
      if (tabletStartProcess) tabletStartProcess.disabled = false;
    }
  }

  window.gestionAlisadoStartProcess = handleTabletStartProcess;

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
  <div class="seccion"><div class="seccion-titulo">Procesos Quimicos Previos</div><div class="procesos-grid">${procesos.map(([l,v]) => `<div class="proceso-item ${v === 'Si' ? 'proceso-si' : 'proceso-no'}">${v === 'Si' ? '?' : '?'} ${esc(l)}</div>`).join('')}</div>${datos.otrosProcesos && datos.otrosProcesos !== '—' ? `<div style="margin-top:6px"><div class="campo-label">Otro:</div><div class="campo-valor">${esc(datos.otrosProcesos)}</div></div>` : ''}</div>
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
  const parentModalEl = root.getElementById('modalFormGestion');
  const checkboxAceptacion = root.getElementById('checkboxAceptacion');
  const btnConfirmar = root.getElementById('btnConfirmarConsentimiento');
  const btnCerrar = root.getElementById('btnCerrarModal');
  const signatureCanvas = root.getElementById('firmaCanvas');
  const signatureCtx = signatureCanvas ? signatureCanvas.getContext('2d') : null;
  const signatureDataInput = root.getElementById('id_firma_consentimiento_data');
  const signatureClearBtn = root.getElementById('btnLimpiarFirma');
  const signaturePlaceholder = root.getElementById('firmaCanvasPlaceholder');
  const signatureStatus = root.getElementById('firmaEstado');
  const errorFirma = root.getElementById('errorFirma');
  const wrapperCheck = root.getElementById('wrapperCheckboxAceptacion');
  const msgCheck = root.getElementById('msgCheckboxError');
  const btnImprimirPDF = root.getElementById('btnImprimirPDF');
  const btnImprimirWord = root.getElementById('btnImprimirWord');
  const modalCliente = root.getElementById('modalCrearCliente');
  const formCliente = root.getElementById('formCrearCliente');
  const btnGuardarCliente = root.getElementById('btnGuardarClienteModal');
  const urlUltima = form.dataset.ultimaGestionUrl || '';
  const tabletShell = root.querySelector('.gestion-form-shell');
  const tabletMode = tabletShell?.dataset.tabletMode === '1';
  const tabletWaitUrl = tabletShell?.dataset.tabletWaitUrl || '';
  const tabletStartUrlTemplate = tabletShell?.dataset.tabletStartUrlTemplate || '';
  const pcLauncherSelectSlot = root.getElementById('pcLauncherSelectSlot');
  const tabletLinkCard = root.getElementById('tabletLinkCard');
  const tabletLinkInput = root.getElementById('tabletLinkInput');
  const tabletLinkCopy = root.getElementById('tabletLinkCopy');
  const tabletStartProcess = root.getElementById('tabletStartProcess');
  const tabletProcessStatus = root.getElementById('tabletProcessStatus');
  const esEdicion = form.dataset.esEdicion === '1';

  let currentStep = 1;
  let signatureDrawing = false;
  let signatureHasInk = false;
  let lastSignaturePoint = null;

  function signatureCanvasMetrics() {
    if (!signatureCanvas || !signatureCtx) return null;
    const rect = signatureCanvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return null;
    const ratio = window.devicePixelRatio || 1;
    return {
      rect,
      width: Math.max(1, Math.round(rect.width * ratio)),
      height: Math.max(1, Math.round(rect.height * ratio)),
      ratio,
    };
  }

  function resizeSignatureCanvas(preserve = false) {
    const metrics = signatureCanvasMetrics();
    if (!metrics || !signatureCtx) return;
    const { width, height, ratio } = metrics;
    const snapshot = preserve && signatureHasInk ? signatureCanvas.toDataURL('image/png') : null;
    signatureCanvas.width = width;
    signatureCanvas.height = height;
    signatureCtx.setTransform(ratio, 0, 0, ratio, 0, 0);
    signatureCtx.lineCap = 'round';
    signatureCtx.lineJoin = 'round';
    signatureCtx.strokeStyle = '#241713';
    signatureCtx.lineWidth = 2.8;
    signatureCtx.clearRect(0, 0, signatureCanvas.width, signatureCanvas.height);
    if (snapshot) {
      const img = new Image();
      img.onload = () => {
        signatureCtx.drawImage(img, 0, 0, signatureCanvas.width / ratio, signatureCanvas.height / ratio);
      };
      img.src = snapshot;
    }
  }

  function syncSignatureData() {
    if (!signatureCanvas || !signatureDataInput) return;
    signatureDataInput.value = signatureHasInk ? signatureCanvas.toDataURL('image/png') : '';
    if (signaturePlaceholder) signaturePlaceholder.style.display = signatureHasInk ? 'none' : 'flex';
    if (signatureStatus) {
      signatureStatus.classList.toggle('ok', signatureHasInk);
      signatureStatus.classList.toggle('error', !signatureHasInk);
      signatureStatus.innerHTML = signatureHasInk
        ? '<i class="bi bi-check-circle-fill"></i><span>Firma registrada</span>'
        : '<i class="bi bi-pencil"></i><span>Sin firma registrada</span>';
    }
    if (errorFirma) errorFirma.style.display = signatureHasInk ? 'none' : 'block';
    if (btnConfirmar) {
      const c = !!selectedCliente();
      const a = !!checkboxAceptacion?.checked;
      btnConfirmar.disabled = !(c && a && signatureHasInk);
    }
  }

  function clearSignatureCanvas() {
    if (!signatureCanvas || !signatureCtx) return;
    resizeSignatureCanvas(false);
    signatureCtx.clearRect(0, 0, signatureCanvas.width, signatureCanvas.height);
    signatureHasInk = false;
    signatureDrawing = false;
    lastSignaturePoint = null;
    syncSignatureData();
  }

  function pointFromEvent(event) {
    const rect = signatureCanvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    return { x, y };
  }

  function drawSignaturePoint(point) {
    if (!signatureCtx) return;
    if (!lastSignaturePoint) {
      lastSignaturePoint = point;
      return;
    }
    signatureCtx.beginPath();
    signatureCtx.moveTo(lastSignaturePoint.x, lastSignaturePoint.y);
    signatureCtx.lineTo(point.x, point.y);
    signatureCtx.stroke();
    lastSignaturePoint = point;
    signatureHasInk = true;
    syncSignatureData();
  }

  function bindSignaturePad() {
    if (!signatureCanvas || !signatureCtx) return;
    syncSignatureData();

    const startDraw = (event) => {
      event.preventDefault();
      if (event.pointerType === 'mouse' && event.button !== 0) return;
      signatureDrawing = true;
      lastSignaturePoint = pointFromEvent(event);
      try { signatureCanvas.setPointerCapture(event.pointerId); } catch {}
    };

    const moveDraw = (event) => {
      if (!signatureDrawing) return;
      event.preventDefault();
      drawSignaturePoint(pointFromEvent(event));
    };

    const endDraw = () => {
      if (!signatureDrawing) return;
      signatureDrawing = false;
      lastSignaturePoint = null;
      syncSignatureData();
    };

    signatureCanvas.addEventListener('pointerdown', startDraw);
    signatureCanvas.addEventListener('pointermove', moveDraw);
    signatureCanvas.addEventListener('pointerup', endDraw);
    signatureCanvas.addEventListener('pointerleave', endDraw);
    signatureCanvas.addEventListener('pointercancel', endDraw);

    signatureClearBtn?.addEventListener('click', (e) => {
      e.preventDefault();
      clearSignatureCanvas();
    });

    window.addEventListener('resize', () => {
      if (signatureCanvas && signatureCanvas.offsetParent !== null) {
        resizeSignatureCanvas(true);
      }
    });

    syncSignatureData();
  }

  function setStep(step) {
    clearStepAlert();
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

  if (!tabletMode && pcLauncherSelectSlot && selectCliente && !pcLauncherSelectSlot.contains(selectCliente)) {
    pcLauncherSelectSlot.appendChild(selectCliente);
  }

  function updateInfoCliente() {
    const c = selectedCliente();
    if (!c) {
      if (infoCliente) infoCliente.textContent = 'Seleccione un cliente en el formulario';
      updateTabletLink();
      return;
    }
    if (infoCliente) infoCliente.innerHTML = `<strong>Nombre:</strong> ${esc(c.nombre)}<br><strong>Documento:</strong> ${esc(c.documento)}`;
    const n = root.getElementById('clienteNombreImpresion'); if (n) n.value = c.nombre;
    const d = root.getElementById('clienteDocumentoImpresion'); if (d) d.value = c.documento;
    updateTabletLink();
  }

  function buildTabletLink(clienteId) {
    if (tabletWaitUrl) return tabletWaitUrl;
    try {
      return new URL('/gestion-alisados/tablet/espera/', window.location.origin).toString();
    } catch {
      return '/gestion-alisados/tablet/espera/';
    }
  }

  function buildTabletStartUrl(clienteId) {
    if (!clienteId || !tabletStartUrlTemplate) return '';
    const relative = tabletStartUrlTemplate.replace(/\/0\/?$/, `/${encodeURIComponent(clienteId)}/`);
    try {
      return new URL(relative, window.location.origin).toString();
    } catch {
      return relative;
    }
  }

  function updateTabletLink() {
    if (!tabletLinkInput) return;
    const clienteId = selectCliente?.value || '';
    const cliente = selectedCliente();
    const href = buildTabletLink(clienteId);
    const startUrl = buildTabletStartUrl(clienteId);
    tabletLinkInput.value = href;
    if (tabletLinkCopy) tabletLinkCopy.disabled = !href;
    if (tabletStartProcess) {
      tabletStartProcess.dataset.startUrl = startUrl || '';
      tabletStartProcess.classList.toggle('is-ready', !!clienteId);
    }
    if (tabletLinkCard) tabletLinkCard.classList.toggle('is-disabled', !href);
    if (tabletProcessStatus) {
      tabletProcessStatus.textContent = clienteId
        ? `Tablet lista en espera para ${cliente?.nombre || 'el cliente seleccionado'}. Enlace: ${href || '—'}`
        : 'Selecciona un cliente para iniciar el proceso desde el PC.';
      tabletProcessStatus.dataset.tone = clienteId ? 'success' : 'warning';
    }
  }

  function toggleSections() {
    const oferta = getField(form, 'es_oferta_especial');
    show(root.getElementById('descripcion_oferta_container'), oferta && oferta.value === 'si');
    show(root.getElementById('promocion_oferta_container'), oferta && oferta.value === 'si');
    show(root.getElementById('medicamento_tiroides_container'), getField(form, 'sufre_tiroides')?.value === 'si');
    show(root.getElementById('frecuencia_ejercicio_container'), getField(form, 'realiza_ejercicio')?.value === 'si');
  }

  function calculateSaldo() {
    calculateMoneySaldoForForm(form);
  }

  function updateImpresion() {
    const estado = datosFormulario(form);
    form._gestionEstado = estado;
  }
  form._gestionUpdateImpresion = updateImpresion;

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
      syncMoneyFields(form);
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
    if (!ok && first) {
      first.focus();
      notifyStepError();
    }
    return ok;
  }

  function validateAllRequiredFields() {
    const missing = [];
    const seen = new Set();
    let first = null;
    form.querySelectorAll('input[required], select[required], textarea[required]').forEach((field) => {
      if (field.disabled || field.type === 'hidden') return;
      const conditional = field.closest('.conditional-field');
      if (conditional && !conditional.classList.contains('show')) return;
      const value = String(field.value || '').trim();
      const emptySelect = field.tagName === 'SELECT' && (value === '' || value === 'None');
      if (!value || emptySelect) {
        field.classList.add('is-invalid');
        if (!first) first = field;
        const label = fieldDisplayName(field);
        if (!seen.has(label)) {
          seen.add(label);
          missing.push(label);
        }
      }
    });
    return { missing, first };
  }

  function validarConsentimiento() {
    const c = !!selectedCliente();
    const a = !!checkboxAceptacion?.checked;
    const f = !!(signatureDataInput?.value && signatureDataInput.value.trim());
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
    bindSignaturePad();
    modalConsentimientoEl.addEventListener('shown.bs.modal', () => {
      resizeSignatureCanvas(false);
      clearSignatureCanvas();
    });
    btnCerrar?.addEventListener('click', () => {
      modal.hide();
      if (parentModalEl && parentModalEl !== modalConsentimientoEl) {
        const parentModal = bootstrap.Modal.getInstance(parentModalEl) || bootstrap.Modal.getOrCreateInstance(parentModalEl);
        parentModal.hide();
      }
    });
    checkboxAceptacion.addEventListener('change', validarConsentimiento);
    signatureDataInput?.addEventListener('input', validarConsentimiento);
    selectCliente?.addEventListener('change', validarConsentimiento);
    btnConfirmar.addEventListener('click', () => {
      const c = selectedCliente();
      if (!c) return setStepAlert('Selecciona un cliente para continuar.', 'warning');
      if (!checkboxAceptacion.checked) return shakeCheckbox();
      const validation = validateAllRequiredFields();
      if (validation.missing.length) {
        if (validation.first) validation.first.focus();
        const step1HasMissing = !!root.querySelector('#step1 .is-invalid');
        const step2HasMissing = !!root.querySelector('#step2 .is-invalid');
        if (step1HasMissing) {
          currentStep = 1;
          setStep(1);
        } else if (step2HasMissing) {
          currentStep = 2;
          setStep(2);
        }
        setStepAlert(`Completa estos campos antes de guardar: ${validation.missing.join(', ')}.`, 'warning');
        modal.hide();
        return;
      }
      syncSignatureData();
      if (!(signatureDataInput && signatureDataInput.value && signatureDataInput.value.trim())) {
        if (errorFirma) errorFirma.style.display = 'block';
        setStepAlert('Registra la firma del cliente para continuar.', 'warning');
        return;
      }
      ['consentimiento_nombre','consentimiento_cedula','consentimiento_fecha','consentimiento_aceptado'].forEach((name) => { form.querySelectorAll(`input[name="${name}"]`).forEach((n) => n.remove()); });
      [['consentimiento_nombre', c.nombre], ['consentimiento_cedula', c.documento], ['consentimiento_fecha', new Date().toLocaleDateString('es-CO', { year:'numeric', month:'long', day:'numeric', hour:'2-digit', minute:'2-digit' })], ['consentimiento_aceptado', 'true']].forEach(([name, value]) => { const i = document.createElement('input'); i.type = 'hidden'; i.name = name; i.value = value; form.appendChild(i); });
      modal.hide(); form.submit();
    });
    validarConsentimiento();
  }

  const syncPcLauncher = async () => {
    updateInfoCliente();
    toggleSections();
    calculateSaldo();
    updateImpresion();
    updateTabletLink();
    await loadHistorial();
  };

  selectCliente?.addEventListener('change', syncPcLauncher);
  selectCliente?.addEventListener('input', syncPcLauncher);
  window.setTimeout(() => {
    if (selectCliente?.value) {
      updateTabletLink();
    }
  }, 0);
  tabletLinkCopy?.addEventListener('click', async () => {
    const href = tabletLinkInput?.value || '';
    if (!href) return setStepAlert('Selecciona un cliente para generar el enlace.', 'warning');
    try {
      await navigator.clipboard.writeText(href);
      toast('Enlace de tablet copiado.', 'success');
    } catch {
      toast('No se pudo copiar el enlace. Selecciónalo manualmente.', 'warning');
    }
  });
  wireMoneyField(getField(form, 'precio_alisado'));
  wireMoneyField(getField(form, 'anticipo_cliente'));
  wireMoneyField(getField(form, 'saldo_pendiente'));
  syncMoneyFields(form);
  calculateSaldo();
  getField(form, 'es_oferta_especial')?.addEventListener('change', () => { toggleSections(); updateImpresion(); });
  getField(form, 'sufre_tiroides')?.addEventListener('change', toggleSections);
  getField(form, 'realiza_ejercicio')?.addEventListener('change', toggleSections);
  getField(form, 'porcentaje_alisado')?.addEventListener('input', function () { const v = parseInt(this.value || '0', 10); if (!Number.isNaN(v)) this.value = Math.min(Math.max(v, 0), 100); updateImpresion(); });
  form.querySelectorAll('input, select, textarea').forEach((el) => { const ev = el.tagName === 'SELECT' ? 'change' : 'input'; el.addEventListener(ev, updateImpresion); });
  form.querySelectorAll('input, select, textarea').forEach((el) => { const ev = el.tagName === 'SELECT' ? 'change' : 'input'; el.addEventListener(ev, clearStepAlert); });

  btnSiguiente?.addEventListener('click', () => {
    if (!validateStep(currentStep)) return;
    if (currentStep < 2) {
      currentStep += 1;
      setStep(currentStep);
    }
  });
  btnAnterior?.addEventListener('click', () => { if (currentStep > 1) { currentStep -= 1; setStep(currentStep); } });
  btnGuardar?.addEventListener('click', (e) => { e.preventDefault(); if (!validateStep(currentStep)) return; if (!selectCliente?.value) return setStepAlert('Selecciona un cliente para continuar.', 'warning'); checkboxAceptacion && (checkboxAceptacion.checked = false); validarConsentimiento(); updateInfoCliente(); modalConsentimientoEl && bootstrap.Modal.getOrCreateInstance(modalConsentimientoEl).show(); });

  btnImprimirPDF?.addEventListener('click', (e) => {
    e.preventDefault();
    const html = generarHTMLDocumento(datosFormulario(form));
    const w = window.open('', '_blank', 'width=860,height=720');
    if (!w) return toast('Permite las ventanas emergentes e intenta de nuevo.', 'warning');
    w.document.open();
    w.document.write(html);
    w.document.close();
    w.focus();
    setTimeout(() => {
      try {
        w.print();
      } catch {}
    }, 700);
  });
  btnImprimirWord?.addEventListener('click', (e) => { e.preventDefault(); const html = generarHTMLDocumento(datosFormulario(form)); const blob = new Blob(['\ufeff' + html], { type: 'application/msword;charset=utf-8' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `Alisado_${(selectedCliente()?.nombre || 'cliente').replace(/\s+/g, '_')}_${new Date().toISOString().slice(0,10)}.doc`; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url); toast('Documento Word descargado correctamente.', 'success'); });

  const step2HasErrors = !!root.querySelector('#step2 .text-danger');
  const step1HasErrors = !!root.querySelector('#step1 .text-danger');
  setStep(step2HasErrors && !step1HasErrors ? 2 : 1);
  updateInfoCliente();
  toggleSections();
  calculateSaldo();
  updateImpresion();
  updateTabletLink();
  initConsentModal();
  wireClienteModal();
  if (selectCliente?.value && !esEdicion) loadHistorial();
}

document.addEventListener('DOMContentLoaded', function () {
  initGestionForm();
});
