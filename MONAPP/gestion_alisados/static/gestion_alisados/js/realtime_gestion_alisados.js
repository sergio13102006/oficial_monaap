(function () {
  const root = document.getElementById('gestionAdminRealtimeRoot');
  const wsUrl = root?.dataset.adminWsUrl || '';
  if (!root || !wsUrl || typeof WebSocket === 'undefined') return;

  const seenEventIds = new Set();
  const latestStateByKey = new Map();
  const statusRank = {
    connected: 10,
    pendiente: 20,
    enviada_a_tablet: 30,
    abierta_en_tablet: 40,
    firmada: 50,
    cancelada: 60,
    expirada: 70,
    error: 80,
    ok: 5,
  };

  let socket = null;
  let reconnectDelay = 1000;
  let reconnectTimer = null;

  function scheduleReconnect() {
    window.clearTimeout(reconnectTimer);
    reconnectTimer = window.setTimeout(connect, reconnectDelay);
    reconnectDelay = Math.min(reconnectDelay * 2, 15000);
  }

  function refreshList() {
    const form = document.getElementById('filtrosForm');
    const target = document.getElementById('gestion-tabla-wrap');
    if (!form || !target) {
      window.location.reload();
      return;
    }

    const url = new URL(form.dataset.ajaxUrl || window.location.pathname, window.location.origin);
    new FormData(form).forEach((value, key) => {
      if (value !== null && value !== '') url.searchParams.set(key, value);
    });

    fetch(url.toString(), { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then((response) => response.text())
      .then((html) => {
        target.innerHTML = html;
      })
      .catch(() => {
        window.location.reload();
      });
  }

  function showMessage(message, type = 'info') {
    if (typeof window.toast === 'function') {
      window.toast(message, type);
      return;
    }
    console.log(`[${type}] ${message}`);
  }

  function eventKey(event) {
    return event.session_id || `tablet:${event.tablet_id || 'global'}`;
  }

  function eventTimestamp(event) {
    const raw = Date.parse(event.timestamp || '');
    return Number.isNaN(raw) ? 0 : raw;
  }

  function eventRank(event) {
    return statusRank[event.status] || 0;
  }

  function validateEventContract(event) {
    return Boolean(
      event &&
      typeof event.type === 'string' &&
      typeof event.event_id === 'string' &&
      typeof event.message_id === 'string' &&
      typeof event.timestamp === 'string' &&
      typeof event.status === 'string' &&
      typeof event.source === 'string' &&
      typeof event.payload === 'object' &&
      event.payload !== null
    );
  }

  function shouldApplyEvent(event) {
    if (!validateEventContract(event)) return false;
    if (seenEventIds.has(event.event_id)) return false;

    seenEventIds.add(event.event_id);
    if (seenEventIds.size > 200) {
      const oldest = seenEventIds.values().next().value;
      seenEventIds.delete(oldest);
    }

    const key = eventKey(event);
    const nextState = {
      timestamp: eventTimestamp(event),
      rank: eventRank(event),
    };
    const previousState = latestStateByKey.get(key);

    if (
      previousState &&
      (
        nextState.timestamp < previousState.timestamp ||
        (nextState.timestamp === previousState.timestamp && nextState.rank < previousState.rank)
      )
    ) {
      return false;
    }

    latestStateByKey.set(key, nextState);
    return true;
  }

  function handleEvent(event) {
    if (!shouldApplyEvent(event)) return;

    switch (event.type) {
      case 'tablet_connected':
        showMessage('Tablet conectada y disponible.', 'success');
        break;
      case 'session_opened':
        showMessage('La tablet abrio la sesion de firma.', 'info');
        break;
      case 'signature_completed':
        showMessage('La firma se completo correctamente.', 'success');
        refreshList();
        break;
      case 'save_error':
        showMessage('Ocurrio un error al guardar la firma.', 'error');
        refreshList();
        break;
      default:
        break;
    }
  }

  function connect() {
    try {
      socket = new WebSocket(wsUrl);
    } catch (error) {
      scheduleReconnect();
      return;
    }

    socket.addEventListener('open', () => {
      reconnectDelay = 1000;
    });

    socket.addEventListener('message', (raw) => {
      try {
        const data = JSON.parse(raw.data);
        handleEvent(data);
      } catch (error) {
        console.warn('Evento realtime invalido', error);
      }
    });

    socket.addEventListener('close', scheduleReconnect);
    socket.addEventListener('error', () => {
      try { socket.close(); } catch (error) {}
    });
  }

  connect();
})();
