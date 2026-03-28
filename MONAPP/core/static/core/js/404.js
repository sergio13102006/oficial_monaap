(function () {
  const body = document.body;
  const root = document.documentElement;
  const prefersReduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (prefersReduced) return;

  let targetX = 0;
  let targetY = 0;
  let currentX = 0;
  let currentY = 0;
  let hasPointer = false;

  function clampInt(value, min, max) {
    return Math.max(min, Math.min(max, Math.round(value)));
  }

  function setSwing(x, y) {
    root.style.setProperty('--swing-x', String(clampInt(x, -100, 100)));
    root.style.setProperty('--swing-y', String(clampInt(y, -100, 100)));
  }

  function onMove(e) {
    const w = window.innerWidth || 1;
    const h = window.innerHeight || 1;
    const px = (e.clientX / w) * 2 - 1; // -1..1
    const py = (e.clientY / h) * 2 - 1; // -1..1

    targetX = px * 100;
    targetY = py * 100;

    if (!hasPointer) {
      hasPointer = true;
      body.classList.add('has-pointer');
    }
  }

  window.addEventListener('mousemove', onMove, { passive: true });

  // Fallback suave: si no hay mouse, que no quede "muerto"
  const start = performance.now();
  function tick(now) {
    const t = (now - start) / 1000;

    if (!hasPointer) {
      targetX = Math.sin(t * 0.85) * 60;
      targetY = Math.cos(t * 0.75) * 60;
    }

    // Interpolación (suave)
    currentX += (targetX - currentX) * 0.08;
    currentY += (targetY - currentY) * 0.08;
    setSwing(currentX, currentY);

    requestAnimationFrame(tick);
  }

  requestAnimationFrame(tick);
})();

