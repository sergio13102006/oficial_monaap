/**
 * notificaciones.js — v3
 * Campana con pepita amarilla para urgentes + modal de confirmación.
 */

(function () {
  'use strict';

  const POLL_INTERVAL = 30_000;

  let panelAbierto   = false;
  let notificaciones = [];

  let wrap, btnNotif, dotRojo, dotUrgente, panel,
      listaEl, contadorEl, btnLeerTodas,
      urlListar, urlLeerTodas, csrfToken;

  /* ══════════════════════════════════════════════════════════════════════════
     INIT
  ══════════════════════════════════════════════════════════════════════════ */
  document.addEventListener('DOMContentLoaded', function () {
    wrap = document.getElementById('notif-wrap');
    if (!wrap) return;

    urlListar    = wrap.dataset.urlListar;
    urlLeerTodas = wrap.dataset.urlLeerTodas;
    csrfToken    = wrap.dataset.csrf;

    _construirHTML();
    _bindEventos();
    _fetchNotificaciones();
    setInterval(_fetchNotificaciones, POLL_INTERVAL);

    // Balanceo al entrar
    setTimeout(function () { _ringBell(); }, 600);
    // Balanceo cada 8s si hay urgentes sin leer
    setInterval(function () {
      if (notificaciones.some(function (n) { return n.urgente; })) {
        _ringBell();
      }
    }, 8000);
  });

  /* ══════════════════════════════════════════════════════════════════════════
     HTML DEL WIDGET
  ══════════════════════════════════════════════════════════════════════════ */
  function _construirHTML() {
    wrap.innerHTML = `

      <!-- ── Botón campana ── -->
      <button class="btn-notif" id="btn-notif"
              aria-label="Notificaciones" title="Notificaciones"
              aria-expanded="false">
        <i class="bi bi-bell-fill"></i>
        <span class="notif-dot"        id="notif-dot"></span>
        <span class="notif-dot-urgente" id="notif-dot-urgente"></span>
      </button>

      <!-- ── Panel emergente ── -->
      <div class="notif-panel" id="notif-panel"
           role="dialog" aria-label="Panel de notificaciones">

        <div class="notif-panel-head">
          <h6>
            <i class="bi bi-bell-fill"></i>
            Notificaciones
            <span class="notif-badge" id="notif-badge" style="display:none"></span>
          </h6>
          <button class="notif-btn-leer-todas" id="notif-leer-todas"
                  title="Marcar todas como leídas">
            <i class="bi bi-check2-all"></i>
          </button>
        </div>

        <div class="notif-panel-body" id="notif-lista">
          <div class="notif-empty">
            <i class="bi bi-bell-slash"></i>
            <p>Sin notificaciones nuevas</p>
          </div>
        </div>

        <div class="notif-panel-footer">
          <span id="notif-footer-txt">Todo al día ✓</span>
        </div>
      </div>

      <!-- ── Modal urgente ── -->
      <div class="notif-modal-overlay" id="notif-modal-overlay">
        <div class="notif-modal" id="notif-modal" role="alertdialog"
             aria-modal="true" aria-labelledby="notif-modal-titulo">
          <div class="notif-modal-head">
            <span class="notif-modal-icono">
              <i class="bi bi-exclamation-octagon-fill"></i>
            </span>
            <div>
              <p class="notif-modal-label">ALERTA URGENTE</p>
              <h5 class="notif-modal-titulo" id="notif-modal-titulo"></h5>
            </div>
          </div>
          <p class="notif-modal-msg" id="notif-modal-msg"></p>
          <div class="notif-modal-footer">
            <button class="notif-modal-btn" id="notif-modal-aceptar">
              <i class="bi bi-check-lg"></i> Aceptar
            </button>
          </div>
        </div>
      </div>
    `;

    btnNotif     = document.getElementById('btn-notif');
    dotRojo      = document.getElementById('notif-dot');
    dotUrgente   = document.getElementById('notif-dot-urgente');
    panel        = document.getElementById('notif-panel');
    listaEl      = document.getElementById('notif-lista');
    contadorEl   = document.getElementById('notif-badge');
    btnLeerTodas = document.getElementById('notif-leer-todas');
  }

  /* ══════════════════════════════════════════════════════════════════════════
     EVENTOS
  ══════════════════════════════════════════════════════════════════════════ */
  function _bindEventos() {
    btnNotif.addEventListener('click', function (e) {
      e.stopPropagation();
      panelAbierto ? _cerrarPanel() : _abrirPanel();
    });

    document.addEventListener('click', function (e) {
      if (panelAbierto && !wrap.contains(e.target)) _cerrarPanel();
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && panelAbierto) _cerrarPanel();
    });

    btnLeerTodas.addEventListener('click', function (e) {
      e.stopPropagation();
      _marcarTodasLeidas();
    });

    // Botón Aceptar del modal urgente
    document.getElementById('notif-modal-aceptar').addEventListener('click', function () {
      const id = parseInt(this.dataset.notifId);
      if (id) _marcarLeida(id, true);
    });
  }

  /* ══════════════════════════════════════════════════════════════════════════
     FETCH
  ══════════════════════════════════════════════════════════════════════════ */
  function _fetchNotificaciones() {
    fetch(urlListar, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      credentials: 'same-origin',
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.permitido) return;

        const totalAnterior   = notificaciones.length;
        const urgentesAntes   = notificaciones.filter(function (n) { return n.urgente; }).length;
        notificaciones        = data.notificaciones;
        const urgentesAhora   = data.urgentes;

        _renderizarLista();
        _actualizarDots(data.total, urgentesAhora);

        // Si llegaron notificaciones nuevas → timbrar
        if (data.total > 0 && data.total !== totalAnterior) {
          _ringBell();
        }
      })
      .catch(function () {});
  }

  /* ══════════════════════════════════════════════════════════════════════════
     RENDER LISTA
  ══════════════════════════════════════════════════════════════════════════ */
  function _renderizarLista() {
    if (!notificaciones.length) {
      listaEl.innerHTML = `
        <div class="notif-empty">
          <i class="bi bi-bell-slash"></i>
          <p>Sin notificaciones nuevas</p>
        </div>`;
      _setFooter('Todo al día ✓');
      return;
    }

    const items = notificaciones.map(function (n) {
      const esUrgente = n.urgente;
      const esWarning = !n.urgente && n.tipo === 'warning';

      const claseExtra = esUrgente ? 'notif-item--urgente'
                       : esWarning ? 'notif-item--warning'
                       : '';

      const badge = esUrgente
        ? '<span class="notif-item-urgente-badge"><i class="bi bi-exclamation-lg"></i> URGENTE</span>'
        : esWarning
        ? '<span class="notif-item-warning-badge"><i class="bi bi-exclamation-triangle"></i> STOCK BAJO</span>'
        : '';

      const btnClase = esUrgente ? 'notif-item-cerrar--urgente' : '';
      const btnIcono = esUrgente ? 'bi-check-lg' : 'bi-x-lg';
      const btnTitle = esUrgente ? 'Aceptar' : 'Marcar como leída';

      return `
        <div class="notif-item ${claseExtra}" data-id="${n.id}">
          <span class="notif-item-icon" style="background:${n.color}">
            <i class="bi ${n.icono}"></i>
          </span>
          <div class="notif-item-content">
            <div class="notif-item-titulo-row">
              <p class="notif-item-titulo">${_escape(n.titulo)}</p>
              ${badge}
            </div>
            <p class="notif-item-msg">${_escape(n.mensaje)}</p>
            <span class="notif-item-time">
              <i class="bi bi-clock"></i> hace ${n.hace}
            </span>
          </div>
          <button class="notif-item-cerrar ${btnClase}"
                  data-id="${n.id}" title="${btnTitle}">
            <i class="bi ${btnIcono}"></i>
          </button>
        </div>`;
    }).join('');

    listaEl.innerHTML = items;
    _setFooter(`${notificaciones.length} notificación${notificaciones.length !== 1 ? 'es' : ''} sin leer`);

    listaEl.querySelectorAll('.notif-item-cerrar').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        _marcarLeida(parseInt(btn.dataset.id), false);
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════════════════
     MODAL URGENTE
  ══════════════════════════════════════════════════════════════════════════ */
  function _mostrarModalUrgente(notif) {
    const overlay  = document.getElementById('notif-modal-overlay');
    const titulo   = document.getElementById('notif-modal-titulo');
    const msg      = document.getElementById('notif-modal-msg');
    const btnAcep  = document.getElementById('notif-modal-aceptar');

    titulo.textContent    = notif.titulo;
    msg.textContent       = notif.mensaje;
    btnAcep.dataset.notifId = notif.id;

    overlay.classList.add('open');
    // Timbrar la campana mientras el modal está visible
    _ringBell();
  }

  function _cerrarModalUrgente() {
    document.getElementById('notif-modal-overlay').classList.remove('open');
  }

  /* ══════════════════════════════════════════════════════════════════════════
     MARCAR LEÍDA (individual)
  ══════════════════════════════════════════════════════════════════════════ */
  function _marcarLeida(id, desdeModal) {
    const url = urlLeerTodas.replace('leer-todas/', id + '/leer/');

    fetch(url, {
      method: 'POST',
      headers: {
        'X-CSRFToken':      csrfToken,
        'X-Requested-With': 'XMLHttpRequest',
      },
      credentials: 'same-origin',
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.success) return;

        if (desdeModal) {
          _cerrarModalUrgente();
        }

        const el = listaEl.querySelector('.notif-item[data-id="' + id + '"]');
        if (el) {
          el.style.transition = 'opacity .3s, transform .3s';
          el.style.opacity    = '0';
          el.style.transform  = 'translateX(20px)';
        }

        setTimeout(function () {
          notificaciones = notificaciones.filter(function (n) { return n.id !== id; });
          _renderizarLista();
          _actualizarDots(
            notificaciones.length,
            notificaciones.filter(function (n) { return n.urgente; }).length
          );
        }, 300);
      });
  }

  /* ══════════════════════════════════════════════════════════════════════════
     MARCAR TODAS LEÍDAS
  ══════════════════════════════════════════════════════════════════════════ */
  function _marcarTodasLeidas() {
    fetch(urlLeerTodas, {
      method: 'POST',
      headers: {
        'X-CSRFToken':      csrfToken,
        'X-Requested-With': 'XMLHttpRequest',
      },
      credentials: 'same-origin',
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.success) return;
        notificaciones = [];
        _renderizarLista();
        _actualizarDots(0, 0);
        _cerrarModalUrgente();
      });
  }

  /* ══════════════════════════════════════════════════════════════════════════
     HELPERS UI
  ══════════════════════════════════════════════════════════════════════════ */
  function _abrirPanel() {
    panel.classList.add('open');
    panelAbierto = true;
    btnNotif.setAttribute('aria-expanded', 'true');
  }

  function _cerrarPanel() {
    panel.classList.remove('open');
    panelAbierto = false;
    btnNotif.setAttribute('aria-expanded', 'false');
  }

  function _actualizarDots(total, urgentes) {
    // Punto rojo normal
    if (total > 0) {
      dotRojo.classList.add('visible');
      contadorEl.textContent  = total > 99 ? '99+' : total;
      contadorEl.style.display = 'inline-flex';
    } else {
      dotRojo.classList.remove('visible');
      contadorEl.style.display = 'none';
    }

    // Pepita amarilla urgente
    if (urgentes > 0) {
      dotUrgente.classList.add('visible');
      dotUrgente.textContent = urgentes > 9 ? '9+' : urgentes;
    } else {
      dotUrgente.classList.remove('visible');
    }
  }

  function _ringBell() {
    const icon = btnNotif ? btnNotif.querySelector('i') : null;
    if (!icon) return;
    icon.classList.remove('bell-ring');
    void icon.offsetWidth;
    icon.classList.add('bell-ring');
    icon.addEventListener('animationend', function () {
      icon.classList.remove('bell-ring');
    }, { once: true });
  }

  function _setFooter(texto) {
    const el = document.getElementById('notif-footer-txt');
    if (el) el.textContent = texto;
  }

  function _escape(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

})();