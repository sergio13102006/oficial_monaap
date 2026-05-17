document.addEventListener('DOMContentLoaded', function () {
    const root = document.getElementById('dashboard-root');
    if (!root) return;

    const totalVentas = parseFloat(root.dataset.totalVentas || '0') || 0;
    const totalCompras = parseFloat(root.dataset.totalCompras || '0') || 0;
    const countVentas = parseInt(root.dataset.countVentas || '0', 10) || 0;
    const countCompras = parseInt(root.dataset.countCompras || '0', 10) || 0;

    const fmt = (value) => '$' + Math.round(value).toLocaleString('es-CO');

    const statVentas = document.getElementById('stat-ventas');
    const statCompras = document.getElementById('stat-compras');
    const statVentasCount = document.getElementById('stat-ventas-count');
    const statComprasCount = document.getElementById('stat-compras-count');
    const statBalance = document.getElementById('stat-balance');
    const gaugeTotal = document.getElementById('gauge-total');

    if (statVentas) statVentas.textContent = fmt(totalVentas);
    if (statCompras) statCompras.textContent = fmt(totalCompras);
    if (statVentasCount) statVentasCount.textContent = String(countVentas);
    if (statComprasCount) statComprasCount.textContent = String(countCompras);

    const balance = totalVentas - totalCompras;
    if (statBalance) {
        statBalance.textContent = fmt(Math.abs(balance));
        statBalance.style.color = balance >= 0 ? '#096931' : '#b41c0b';
    }

    const grand = totalVentas + totalCompras;
    if (gaugeTotal) gaugeTotal.textContent = fmt(grand);

    document.querySelectorAll('.sbar-fill[data-fill-width]').forEach((fill) => {
        fill.style.width = `${fill.dataset.fillWidth || '0'}%`;
    });

    const fechaEl = document.getElementById('hero-fecha');
    const horaEl = document.getElementById('hero-hora');
    if (fechaEl && horaEl) {
        const dias = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];
        const meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];

        const actualizar = () => {
            const n = new Date();
            fechaEl.textContent = dias[n.getDay()] + ', ' + n.getDate() + ' de ' + meses[n.getMonth()] + ' ' + n.getFullYear();
            horaEl.textContent = String(n.getHours()).padStart(2, '0') + ':' + String(n.getMinutes()).padStart(2, '0') + ':' + String(n.getSeconds()).padStart(2, '0');
        };

        actualizar();
        setInterval(actualizar, 1000);
    }

    function detalleHTML(tipo) {
        const isVentas = tipo === 'ventas';
        const total = isVentas ? totalVentas : totalCompras;
        const count = isVentas ? countVentas : countCompras;
        const pct = grand > 0 ? total / grand : 0;
        const titulo = isVentas ? 'Ventas' : 'Compras';
        const color = isVentas ? 'var(--g)' : 'var(--r)';

        return `
          <div style="text-align:left;">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
              <span style="width:12px;height:12px;border-radius:50%;background:${color};display:inline-block;"></span>
              <div style="font-weight:800;letter-spacing:.02em;">${titulo}</div>
            </div>
            <div style="display:grid;grid-template-columns:1fr auto;gap:6px 14px;align-items:center;">
              <div style="color:#6b5a50;">Total</div><div style="font-weight:800;">${fmt(total)}</div>
              <div style="color:#6b5a50;">Registros</div><div style="font-weight:800;">${count}</div>
              <div style="color:#6b5a50;">Participación</div><div style="font-weight:800;">${Math.round(pct * 100)}%</div>
            </div>
          </div>
        `;
    }

    let gaugeTooltip = null;
    let hideTooltipTimer = null;

    function getGaugeTooltip() {
        if (gaugeTooltip) return gaugeTooltip;
        gaugeTooltip = document.createElement('div');
        gaugeTooltip.id = 'gauge-hover-tooltip';
        gaugeTooltip.style.position = 'fixed';
        gaugeTooltip.style.zIndex = '9999';
        gaugeTooltip.style.minWidth = '220px';
        gaugeTooltip.style.maxWidth = '280px';
        gaugeTooltip.style.background = 'rgba(20,20,20,.94)';
        gaugeTooltip.style.color = '#fff';
        gaugeTooltip.style.border = '1px solid rgba(255,255,255,.14)';
        gaugeTooltip.style.borderRadius = '14px';
        gaugeTooltip.style.boxShadow = '0 14px 36px rgba(0,0,0,.35)';
        gaugeTooltip.style.padding = '12px';
        gaugeTooltip.style.pointerEvents = 'none';
        gaugeTooltip.style.opacity = '0';
        gaugeTooltip.style.transform = 'translateY(6px)';
        gaugeTooltip.style.transition = 'opacity .12s ease, transform .12s ease';
        document.body.appendChild(gaugeTooltip);

        const hide = () => {
            if (!gaugeTooltip) return;
            gaugeTooltip.style.opacity = '0';
            gaugeTooltip.style.transform = 'translateY(6px)';
        };
        window.addEventListener('scroll', hide, { passive: true });
        window.addEventListener('resize', hide);
        return gaugeTooltip;
    }

    function posicionarTooltip(ev) {
        const pop = getGaugeTooltip();
        const x = ev && ev.clientX ? ev.clientX : window.innerWidth / 2;
        const y = ev && ev.clientY ? ev.clientY : window.innerHeight / 2;
        const pad = 14;

        pop.style.left = '-9999px';
        pop.style.top = '-9999px';

        const rect = pop.getBoundingClientRect();
        const left = Math.min(Math.max(pad, x + 14), window.innerWidth - rect.width - pad);
        const top = Math.min(Math.max(pad, y + 14), window.innerHeight - rect.height - pad);
        pop.style.left = left + 'px';
        pop.style.top = top + 'px';
    }

    function mostrarTooltip(tipo, ev) {
        const pop = getGaugeTooltip();
        if (hideTooltipTimer) {
            clearTimeout(hideTooltipTimer);
            hideTooltipTimer = null;
        }
        pop.innerHTML = detalleHTML(tipo);
        posicionarTooltip(ev);
        pop.style.opacity = '1';
        pop.style.transform = 'translateY(0)';
    }

    function moverTooltip(ev) {
        if (!gaugeTooltip || gaugeTooltip.style.opacity !== '1') return;
        posicionarTooltip(ev);
    }

    function ocultarTooltip() {
        if (!gaugeTooltip) return;
        if (hideTooltipTimer) clearTimeout(hideTooltipTimer);
        hideTooltipTimer = setTimeout(() => {
            if (!gaugeTooltip) return;
            gaugeTooltip.style.opacity = '0';
            gaugeTooltip.style.transform = 'translateY(6px)';
        }, 70);
    }

    [
        ['arc-ventas', 'ventas'],
        ['arc-ventas-outline', 'ventas'],
        ['arc-compras', 'compras'],
        ['arc-compras-outline', 'compras'],
    ].forEach(([id, tipo]) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.style.cursor = 'default';
        el.addEventListener('mouseenter', function (ev) { mostrarTooltip(tipo, ev); });
        el.addEventListener('mousemove', function (ev) { moverTooltip(ev); });
        el.addEventListener('mouseleave', function () { ocultarTooltip(); });
    });
});
