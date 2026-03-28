document.addEventListener('DOMContentLoaded', () => {
  // ===============================
  // ELEMENTOS
  // ===============================
  const header = document.querySelector('.header');
  const footer = document.querySelector('.footer');
  const nav = document.querySelector('.nav-glass');
  const toggle = document.querySelector('[data-nav-toggle]');
  const backdrop = document.querySelector('[data-nav-backdrop]');
  const navItems = document.querySelectorAll('.nav-item');
  const logo = document.querySelector('.logo svg');

  function setNav(open) {
    if (!header) return;
    header.classList.toggle('nav-open', !!open);
    if (toggle) toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  }

  if (toggle && header) {
    const handleToggle = (event) => {
      event.preventDefault();
      setNav(!header.classList.contains('nav-open'));
    };

    toggle.addEventListener('click', handleToggle);
    toggle.addEventListener('touchend', handleToggle, { passive: false });
    toggle.addEventListener('pointerup', handleToggle);
  }

  if (backdrop) {
    backdrop.addEventListener('click', () => setNav(false));
  }

  if (nav) {
    nav.querySelectorAll('a[href^="#"]').forEach((link) => {
      link.addEventListener('click', () => setNav(false));
    });
  }

  // ===============================
  // SCROLL HEADER + FOOTER
  // ===============================
  window.addEventListener('scroll', () => {

    // HEADER SCROLL (solo si existe)
    if (header) {
      if (window.scrollY > 50) {
        header.classList.add('scrolled');
      } else {
        header.classList.remove('scrolled');
      }
    }

    // FOOTER VISIBLE AL FINAL
    if (footer) {
      if (window.scrollY + window.innerHeight >= document.body.scrollHeight - 50) {
        footer.classList.add('visible');
      } else {
        footer.classList.remove('visible');
      }
    }
  });

  // ===============================
  // HOVER EFECTO PÍLDORA (SUAVE)
  // ===============================
  if (navItems && navItems.length) {
    navItems.forEach(item => {
      item.addEventListener('mouseenter', () => {
        item.style.transform = 'translateY(-2px)';
      });

      item.addEventListener('mouseleave', () => {
        item.style.transform = 'translateY(0)';
      });
    });
  }

  // ===============================
  // UTILIDADES LOGO COLOR
  // ===============================
  function isLightColor(rgb) {
    // Maneja rgb() y rgba()
    const result = rgb && rgb.match(/\d+/g);
    if (!result || result.length < 3) return false;

    const r = parseInt(result[0], 10);
    const g = parseInt(result[1], 10);
    const b = parseInt(result[2], 10);

    // fórmula de luminancia
    const brightness = (r * 299 + g * 587 + b * 114) / 1000;
    return brightness > 160; // > claro, < oscuro
  }

  function updateLogoColor() {
    // Si no existe header o logo en esta página, no hacemos nada
    if (!header || !logo) return;

    const headerRect = header.getBoundingClientRect();

    const x = window.innerWidth / 2;
    const y = headerRect.bottom + 1;

    const elementBehind = document.elementFromPoint(x, y);
    if (!elementBehind) return;

    const bg = window.getComputedStyle(elementBehind).backgroundColor;

    if (isLightColor(bg)) {
      logo.style.color = '#000';
    } else {
      logo.style.color = '#fff';
    }
  }

  // ===============================
  // NAVBAR OSCURO FORZADO EN INFINITE
  // ===============================
  const infiniteSection = document.getElementById('infinite');

  function updateNavbarInfiniteMode() {
    if (!header || !infiniteSection) return;

    const sectionTop = infiniteSection.offsetTop;
    const sectionBottom = sectionTop + infiniteSection.offsetHeight;
    const scrollPos = window.scrollY + window.innerHeight / 2;

    if (scrollPos >= sectionTop && scrollPos <= sectionBottom) {
      // Estamos en infinite
      header.classList.add('navbar-dark');

      // Forzamos logo negro
      if (logo) {
        logo.style.color = '#000';
      }
    } else {
      // Fuera de infinite
      header.classList.remove('navbar-dark');

      // Devolvemos control a la lógica automática
      updateLogoColor();
    }
  }

  // ===============================
  // ESCUCHADORES (solo si aplica)
  // ===============================
  // Nota: DOMContentLoaded ya garantiza que el DOM existe,
  // pero "load" puede ser útil si dependes de imágenes/layout final.
  window.addEventListener('scroll', updateNavbarInfiniteMode);
  window.addEventListener('resize', updateNavbarInfiniteMode);
  window.addEventListener('load', updateNavbarInfiniteMode);

  window.addEventListener('scroll', updateLogoColor);
  window.addEventListener('resize', updateLogoColor);
  window.addEventListener('load', updateLogoColor);

  // Primera ejecución (para que no espere al primer scroll)
  updateNavbarInfiniteMode();
  updateLogoColor();
});
