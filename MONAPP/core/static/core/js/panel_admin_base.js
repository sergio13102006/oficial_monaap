document.addEventListener('DOMContentLoaded', function () {
    initSidebar();
    initAlerts();
    initActiveLinks();
    initTooltips();
    if (typeof initIconSwapButtons === 'function') {
        initIconSwapButtons();
    }
    initAccessibility();
    initDashboardChart();
    initAjaxFilterForms();
    initInstantFilterForms();
    initSearchToggle();
    if (typeof initSmartFormValidation === 'function') {
        initSmartFormValidation();
    }
});
// ==================== SIDEBAR ====================
function initSidebar() {
    const sidebarHandle = document.getElementById('sidebar-handle');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('main-content');

    if (!sidebar || !mainContent) return;

    function toggleSidebar() {
        if (window.innerWidth <= 991) {
            sidebar.classList.toggle('active');
            document.body.classList.toggle('sidebar-mobile-open', sidebar.classList.contains('active'));
            return;
        }

        sidebar.classList.toggle('collapsed');
        mainContent.classList.toggle('expanded');

        const isCollapsed = sidebar.classList.contains('collapsed');
        document.body.classList.toggle('sidebar-collapsed', isCollapsed);
        localStorage.setItem('sidebarCollapsed', isCollapsed);
    }

    if (sidebarHandle && sidebarHandle.dataset.sidebarBound !== 'true') {
        sidebarHandle.dataset.sidebarBound = 'true';
        sidebarHandle.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            toggleSidebar();
        });
    }

    // ── Conectar botón del topbar  ──
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function (e) {
            e.stopPropagation();
            toggleSidebar();
        });
    }

    // ── Restaurar estado guardado ──
    // Default: sidebar abierto. Solo colapsar si el usuario lo cerró manualmente.
    const sidebarCollapsed = localStorage.getItem('sidebarCollapsed');
    if (sidebarCollapsed === 'true' && window.innerWidth > 991) {
        sidebar.classList.add('collapsed');
        mainContent.classList.add('expanded');
        document.body.classList.add('sidebar-collapsed');
    } else {
        // Asegurar que empiece abierto (quitar cualquier clase residual)
        sidebar.classList.remove('collapsed');
        mainContent.classList.remove('expanded');
        document.body.classList.remove('sidebar-collapsed');
        localStorage.setItem('sidebarCollapsed', 'false');
    }

    document.addEventListener('click', function (e) {
        if (window.innerWidth > 991) return;
        if (!sidebar.classList.contains('active')) return;
        if (sidebar.contains(e.target) || (sidebarHandle && sidebarHandle.contains(e.target))) return;

        sidebar.classList.remove('active');
        document.body.classList.remove('sidebar-mobile-open');
    });
}

// ==================== ALERTAS ====================
function initAlerts() {
    const alerts = document.querySelectorAll('.alert');

    alerts.forEach(function (alert) {
        setTimeout(function () {
            if (typeof bootstrap !== 'undefined' && bootstrap.Alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, 5000);
    });
}

// ==================== LINK ACTIVO ====================
function initActiveLinks() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.sidebar-nav .nav-link');

    navLinks.forEach(function (link) {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });

    document.querySelectorAll('.submenu').forEach(function (submenu) {
        const activeChild = submenu.querySelector('.nav-link.active');
        if (activeChild) {
            submenu.classList.add('show');
            const toggle = submenu.previousElementSibling;
            if (toggle) {
                toggle.setAttribute('aria-expanded', 'true');
                toggle.classList.add('active');
            }
        }
    });
}

// ==================== TOOLTIPS ====================
function initTooltips() {
    if (typeof bootstrap === 'undefined' || !bootstrap.Tooltip) return;

    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipTriggerList.forEach(function (el) {
        new bootstrap.Tooltip(el);
    });
}

// ==================== ACCESIBILIDAD ====================
function initAccessibility() {
    if (typeof SiennaAccessibility !== 'undefined') {
        SiennaAccessibility.init();
    }
}

// ==================== CHART ====================
function initDashboardChart() {
    window.initDashboardChart = function (canvasId, data, options) {
        const ctx = document.getElementById(canvasId);
        if (ctx && typeof Chart !== 'undefined') {
            new Chart(ctx, {
                type: data.type || 'bar',
                data: data,
                options: options || {}
            });
        }
    };
}
// =========================
// TOGGLE BÚSQUEDA GLOBAL
// =========================
function initSearchToggle() {
    const wrappers = document.querySelectorAll('.search-toggle-wrapper');

    wrappers.forEach(function (wrapper) {
        if (wrapper.dataset.searchInit === 'true') return;
        wrapper.dataset.searchInit = 'true';

        const btn = wrapper.querySelector('.btn-search-toggle');
        const box = wrapper.querySelector('.search-toggle-box');
        const input = wrapper.querySelector('.search-toggle-input');
        const form = wrapper.closest('form');

        if (!btn || !box || !input || !form) return;

        function openSearch() {
            wrapper.classList.add('is-open');
            box.classList.add('is-open');
            btn.setAttribute('aria-expanded', 'true');

            setTimeout(function () {
                input.focus();
                const len = input.value.length;
                input.setSelectionRange(len, len);
            }, 120);
        }

        function closeSearch() {
            wrapper.classList.remove('is-open');
            box.classList.remove('is-open');
            btn.setAttribute('aria-expanded', 'false');
        }

        function animateButton() {
            btn.classList.add('rotating');
            setTimeout(function () {
                btn.classList.remove('rotating');
            }, 380);
        }

        function submitSearch(immediate = false) {
            if (typeof form._submitAjaxSearch === 'function') {
                form._submitAjaxSearch(immediate);
            } else {
                form.submit();
            }
        }

        if (input.value.trim()) {
            openSearch();
        }

        btn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();

            animateButton();

            if (!wrapper.classList.contains('is-open')) {
                openSearch();
                return;
            }

            if (input.value.trim()) {
                submitSearch(true);
                return;
            }

            closeSearch();
        });

        input.addEventListener('click', function (e) {
            e.stopPropagation();
        });

        input.addEventListener('focus', function () {
            openSearch();
        });

        input.addEventListener('input', function () {
            wrapper.classList.add('is-open');
            box.classList.add('is-open');
            btn.setAttribute('aria-expanded', 'true');
            submitSearch(false);
        });

        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                submitSearch(true);
            }

            if (e.key === 'Escape') {
                e.preventDefault();

                if (input.value.trim()) {
                    input.value = '';
                    submitSearch(true);
                } else {
                    closeSearch();
                }
            }
        });

        document.addEventListener('click', function (e) {
            if (!wrapper.classList.contains('is-open')) return;
            if (wrapper.contains(e.target)) return;

            if (!input.value.trim()) {
                closeSearch();
            }
        });
    });
}

// ==================== FUNCIONES GLOBALES ====================
function showNotification(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.role = 'alert';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    const messagesContainer =
        document.querySelector('.messages-container') ||
        document.querySelector('.content-wrapper');

    if (messagesContainer) {
        messagesContainer.insertBefore(alertDiv, messagesContainer.firstChild);

        setTimeout(function () {
            if (typeof bootstrap !== 'undefined' && bootstrap.Alert) {
                const bsAlert = new bootstrap.Alert(alertDiv);
                bsAlert.close();
            }
        }, 5000);
    }
}

function confirmAction(message) {
    console.warn('confirmAction() is deprecated. Use data-confirm attributes. Falling back to window.confirm for legacy code.');
    return confirm(message || '¿Estás seguro de realizar esta acción?');
}

window.showNotification = showNotification;
window.confirmAction = confirmAction;
function initAjaxFilterForms() {
    const forms = document.querySelectorAll('.js-ajax-search-form');

    forms.forEach(function (form) {
        if (form.dataset.ajaxFormInit === 'true') return;
        form.dataset.ajaxFormInit = 'true';

        const ajaxUrl = form.dataset.ajaxUrl || form.getAttribute('action') || window.location.pathname;
        const ajaxTargetSelector = form.dataset.ajaxTarget;
        const ajaxDebounce = parseInt(form.dataset.ajaxDebounce || '300', 10);

        let debounceTimer = null;
        let activeController = null;
        let lastQueryString = null;

        async function runAjaxRequest(submitter = null) {
            const target = document.querySelector(ajaxTargetSelector);

            if (!target) {
                form.submit();
                return;
            }

            const formData = new FormData(form);
            if (submitter && submitter.name) {
                formData.set(submitter.name, submitter.value || "");
            }
            const params = new URLSearchParams(formData);
            const queryString = params.toString();
            const url = `${ajaxUrl}?${queryString}`;

            if (queryString === lastQueryString) return;
            lastQueryString = queryString;

            if (activeController) {
                activeController.abort();
            }

            activeController = new AbortController();

            try {
                target.classList.remove('is-entering', 'is-ready');
                target.classList.add('is-loading');

                const response = await fetch(url, {
                    method: 'GET',
                    credentials: 'same-origin',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    signal: activeController.signal
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const html = await response.text();

                target.classList.remove('is-loading');
                target.classList.add('is-entering');

                requestAnimationFrame(function () {
                    target.innerHTML = html;

                    requestAnimationFrame(function () {
                        target.classList.remove('is-entering');
                        target.classList.add('is-ready');
                    });
                });

                if (window.history && window.history.replaceState) {
                    window.history.replaceState({}, '', url);
                }

                if (typeof initTooltips === 'function') {
                    initTooltips();
                }
            } catch (error) {
                if (error.name === 'AbortError') return;

                console.error('Error en filtros AJAX:', error);
                target.classList.remove('is-loading', 'is-entering');
                target.classList.add('is-ready');
                form.submit();
            }
        }

        function submitAjaxForm(immediate = false, submitter = null) {
            clearTimeout(debounceTimer);

            if (immediate) {
                runAjaxRequest(submitter);
                return;
            }

            debounceTimer = setTimeout(() => runAjaxRequest(submitter), ajaxDebounce);
        }

        form.addEventListener('submit', function (e) {
            e.preventDefault();
            submitAjaxForm(true, e.submitter || null);
        });

        form.querySelectorAll('select, input[type="date"], input[type="checkbox"], input[type="radio"]').forEach(function (field) {
            field.addEventListener('change', function () {
                submitAjaxForm(true);
            });
        });

        form.querySelectorAll('input[type="text"], input[type="search"], textarea').forEach(function (field) {
            field.addEventListener('input', function () {
                submitAjaxForm(false);
            });
        });

        form._submitAjaxSearch = submitAjaxForm;
    });
}

function initInstantFilterForms() {
    const forms = document.querySelectorAll('.js-instant-filter-form');

    forms.forEach(function (form) {
        if (form.dataset.instantFilterInit === 'true') return;
        form.dataset.instantFilterInit = 'true';

        let debounceTimer = null;
        const debounceMs = parseInt(form.dataset.instantFilterDebounce || '250', 10);

        function submitNow() {
            form.submit();
        }

        function queueSubmit(immediate = false) {
            clearTimeout(debounceTimer);

            if (immediate) {
                submitNow();
                return;
            }

            debounceTimer = setTimeout(submitNow, debounceMs);
        }

        form.addEventListener('submit', function (e) {
            e.preventDefault();
            submitNow();
        });

        form.querySelectorAll('select, input[type="date"], input[type="checkbox"], input[type="radio"]').forEach(function (field) {
            field.addEventListener('change', function () {
                queueSubmit(true);
            });
        });

        form.querySelectorAll('input[type="text"], input[type="search"], textarea').forEach(function (field) {
            field.addEventListener('input', function () {
                queueSubmit(false);
            });
        });
    });
}
