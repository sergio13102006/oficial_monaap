document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginModalForm') || document.getElementById('loginForm');
    const attemptsInfo = document.getElementById('loginAttemptsInfo');
    const toggle = document.getElementById('togglePassword');
    const passInput = document.getElementById('password');
    const captchaShell = document.getElementById('loginCaptchaShell');
    const captchaHelp = document.getElementById('loginCaptchaHelp') || document.getElementById('captchaHelpText');
    const captchaWidgetEl = document.getElementById('loginRecaptchaWidget');
    const captchaSiteKey = captchaShell?.dataset?.siteKey || window.LOGIN_RECAPTCHA_SITE_KEY || '';
    const captchaEnabled = captchaShell?.dataset?.enabled === '1' && !!captchaSiteKey;

    let captchaWidgetId = null;
    let captchaVisible = false;
    let captchaRenderReady = false;

    if (toggle && passInput) {
        toggle.addEventListener('click', () => {
            const isPass = passInput.type === 'password';
            passInput.type = isPass ? 'text' : 'password';
            toggle.classList.toggle('bi-eye');
            toggle.classList.toggle('bi-eye-slash');
        });
    }

    document.querySelectorAll('.login-alert[data-autoclose]').forEach((el) => {
        const delay = parseInt(el.dataset.autoclose, 10);
        if (Number.isNaN(delay) || delay <= 0) return;

        const bar = el.querySelector('.alert-progress-bar');
        if (bar) {
            bar.style.transition = `width ${delay}ms linear`;
            requestAnimationFrame(() => {
                bar.style.width = '0%';
            });
        }

        setTimeout(() => {
            try {
                bootstrap.Alert.getOrCreateInstance(el).close();
            } catch (error) {
                el.remove();
            }
        }, delay);
    });

    const particlesContainer = document.getElementById('particles');
    if (particlesContainer) {
        for (let i = 0; i < 25; i += 1) {
            const dot = document.createElement('span');
            dot.className = 'particle';
            dot.style.left = `${Math.random() * 100}%`;
            dot.style.animationDuration = `${4 + Math.random() * 8}s`;
            dot.style.animationDelay = `${Math.random() * 5}s`;
            dot.style.width = dot.style.height = `${2 + Math.random() * 4}px`;
            particlesContainer.appendChild(dot);
        }
    }

    const setAttemptsMessage = (attempts, blockedMinutes, message) => {
        if (!attemptsInfo) return;

        if (!message && !attempts && !blockedMinutes) {
            attemptsInfo.style.display = 'none';
            attemptsInfo.textContent = '';
            attemptsInfo.classList.remove('is-blocked');
            return;
        }

        const parts = [];
        if (message) parts.push(message);
        if (attempts) parts.push(`Intentos: ${attempts}`);
        if (blockedMinutes) parts.push(`Espera: ${blockedMinutes} minuto(s).`);

        attemptsInfo.textContent = parts.join(' · ');
        attemptsInfo.style.display = 'block';
        attemptsInfo.classList.toggle('is-blocked', !!blockedMinutes);
    };

    const resetCaptchaWidget = () => {
        if (!captchaEnabled || captchaWidgetId === null || !window.grecaptcha) return;
        try {
            window.grecaptcha.reset(captchaWidgetId);
        } catch (error) {
            console.warn('No se pudo reiniciar reCAPTCHA:', error);
        }
    };

    const ensureCaptchaVisible = async () => {
        if (!captchaEnabled || !captchaShell || !captchaWidgetEl) return;
        captchaShell.classList.remove('d-none');
        captchaShell.classList.add('is-visible');
        captchaVisible = true;

        if (captchaRenderReady || !window.grecaptcha || typeof window.grecaptcha.render !== 'function') {
            return;
        }

        captchaWidgetId = window.grecaptcha.render(captchaWidgetEl, {
            sitekey: captchaSiteKey,
            callback: () => {
                if (captchaHelp) {
                    captchaHelp.textContent = 'Verificación completada. Ya puedes ingresar.';
                }
            },
            'expired-callback': () => {
                if (captchaHelp) {
                    captchaHelp.textContent = 'La verificación expiró. Completa el captcha otra vez.';
                }
            },
            'error-callback': () => {
                if (captchaHelp) {
                    captchaHelp.textContent = 'No se pudo cargar la verificación. Intenta nuevamente.';
                }
            },
        });

        captchaRenderReady = true;
    };

    const getCaptchaToken = () => {
        if (!captchaEnabled || !window.grecaptcha || captchaWidgetId === null) return '';
        try {
            return window.grecaptcha.getResponse(captchaWidgetId) || '';
        } catch (error) {
            return '';
        }
    };

    if (captchaEnabled) {
        const waitForRecaptcha = () => {
            if (window.grecaptcha && typeof window.grecaptcha.render === 'function') {
                if (captchaShell?.dataset?.enabled === '1' && captchaShell.dataset.autoshow === '1') {
                    ensureCaptchaVisible();
                }
                return;
            }
            setTimeout(waitForRecaptcha, 120);
        };
        waitForRecaptcha();
    }

    if (loginForm) {
        loginForm.addEventListener('submit', async (event) => {
            event.preventDefault();

            const captchaToken = getCaptchaToken();
            const captchaIsActive = captchaEnabled && captchaShell && !captchaShell.classList.contains('d-none');
            if (captchaIsActive && !captchaToken) {
                if (captchaHelp) {
                    captchaHelp.textContent = 'Completa la verificación para continuar.';
                }
                return;
            }

            const submitBtn = loginForm.querySelector('button[type="submit"]');
            const originalText = submitBtn ? submitBtn.innerHTML : '';
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = 'Verificando...';
            }

            try {
                const formData = new FormData(loginForm);
                if (captchaEnabled && captchaToken) {
                    formData.set('g-recaptcha-response', captchaToken);
                }
                formData.set('ajax_login', '1');

                const response = await fetch(loginForm.action, {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    body: formData,
                });

                const data = await response.json().catch(() => ({}));

                if (response.ok && data.success) {
                    setAttemptsMessage('', '', '');
                    window.location.href = data.redirect || '/';
                    return;
                }

                if (data.captcha_required) {
                    await ensureCaptchaVisible();
                    resetCaptchaWidget();
                    if (captchaHelp) {
                        captchaHelp.textContent = 'La verificación de seguridad es obligatoria para continuar.';
                    }
                } else if (captchaEnabled) {
                    resetCaptchaWidget();
                }

                setAttemptsMessage(
                    data.attempts || 0,
                    data.blocked_minutes || 0,
                    data.message || 'Credenciales inválidas.'
                );

                if (passInput) passInput.focus();
            } catch (error) {
                setAttemptsMessage('', '', 'No se pudo validar el ingreso. Intenta de nuevo.');
            } finally {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalText;
                }
            }
        });
    }
});
