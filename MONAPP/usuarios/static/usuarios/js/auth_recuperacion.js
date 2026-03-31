(function () {
    function startCanvas() {
        var c = document.getElementById('leftCanvas');
        if (!c) return;
        var ctx = c.getContext('2d');
        function resize() { c.width = c.parentElement.offsetWidth; c.height = c.parentElement.offsetHeight; }
        resize();
        window.addEventListener('resize', resize);
        var bs = [];
        for (var i = 0; i < 15; i++) {
            bs.push({ x: Math.random() * c.width, y: Math.random() * c.height, r: 15 + Math.random() * 20, dx: (Math.random() - .5) * .6, dy: (Math.random() - .5) * .6, a: .4 + Math.random() * .35 });
        }
        function draw() {
            ctx.clearRect(0, 0, c.width, c.height);
            bs.forEach(function (b) {
                ctx.beginPath();
                ctx.fillStyle = 'rgba(255,255,255,' + b.a + ')';
                ctx.arc(b.x, b.y, b.r, 0, Math.PI * 2);
                ctx.fill();
                b.x += b.dx; b.y += b.dy;
                if (b.x <= b.r || b.x >= c.width - b.r) b.dx *= -1;
                if (b.y <= b.r || b.y >= c.height - b.r) b.dy *= -1;
            });
            requestAnimationFrame(draw);
        }
        draw();
    }

    function setupRecoveryEmail() {
        var emailInp = document.getElementById('email');
        var emailErr = document.getElementById('email-error');
        var form = document.getElementById('recuperarForm');
        var btnEnviar = document.getElementById('btnEnviar');
        var RE_EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
        var requiresEmailFormat = emailInp && emailInp.type === 'email';
        if (!emailInp || !form || !btnEnviar) return;

        function setEmailState(valid, msg) {
            if (emailErr) emailErr.textContent = msg || '';
            emailInp.classList.remove('input-invalid', 'input-valid');
            if (valid === true) emailInp.classList.add('input-valid');
            if (valid === false) emailInp.classList.add('input-invalid');
        }

        function validateEmail() {
            var v = emailInp.value.trim();
            if (!v) { setEmailState(null, ''); return false; }
            if (requiresEmailFormat && !RE_EMAIL.test(v)) {
                setEmailState(false, 'Ingresa un correo válido (ej: tu@correo.com)');
                return false;
            }
            setEmailState(true, '');
            return true;
        }

        emailInp.addEventListener('input', validateEmail);
        emailInp.addEventListener('blur', validateEmail);
        form.addEventListener('submit', function (e) {
            if (!validateEmail()) {
                e.preventDefault();
                emailInp.focus();
                return;
            }
            btnEnviar.disabled = true;
            btnEnviar.textContent = 'Enviando...';
        });
    }

    function setupVerifyCode() {
        var inp = document.getElementById('codigoInput');
        var counter = document.getElementById('codeCounter');
        var form = document.getElementById('codigoForm');
        var btn = document.getElementById('btnVerificar');
        if (!inp || !counter || !form || !btn) return;

        function updateCounter() {
            var len = inp.value.length;
            counter.className = 'code-counter';
            if (len === 0) { counter.textContent = ''; return; }
            if (len === 6) {
                counter.textContent = '\u2713 Codigo completo';
                counter.classList.add('complete');
                inp.style.borderColor = 'var(--gold)';
                inp.style.boxShadow = '0 0 0 4px rgba(201,169,110,.2)';
            } else {
                counter.textContent = (6 - len) + ' digito(s) restante(s)';
                inp.style.borderColor = '';
                inp.style.boxShadow = '';
            }
        }

        inp.addEventListener('keypress', function (e) {
            if (!/[0-9]/.test(e.key) && !['Backspace','Delete','Tab','ArrowLeft','ArrowRight'].includes(e.key)) {
                e.preventDefault();
            }
        });
        inp.addEventListener('input', function () { this.value = this.value.replace(/\D/g, '').slice(0, 6); updateCounter(); });
        inp.addEventListener('paste', function (e) {
            e.preventDefault();
            var pasted = (e.clipboardData || window.clipboardData).getData('text');
            var digits = pasted.replace(/\D/g, '').slice(0, 6);
            this.value = digits;
            this.dispatchEvent(new Event('input'));
        });
        form.addEventListener('submit', function (e) {
            if (inp.value.length !== 6) {
                e.preventDefault();
                inp.style.borderColor = '#e74c3c';
                inp.style.boxShadow = '0 0 0 4px rgba(231,76,60,.1)';
                counter.textContent = 'El codigo debe tener exactamente 6 digitos.';
                counter.className = 'code-counter error';
                inp.focus();
                return;
            }
            btn.disabled = true;
            btn.textContent = 'Verificando...';
        });
    }

    function setupNewPassword() {
        var p1 = document.getElementById('p1');
        var p2 = document.getElementById('p2');
        var segs = [document.getElementById('b1'), document.getElementById('b2'), document.getElementById('b3'), document.getElementById('b4'), document.getElementById('b5')];
        var stxt = document.getElementById('stxt');
        var mtxt = document.getElementById('mtxt');
        var btnSave = document.getElementById('btnSave');
        var requirementsCard = document.getElementById('passwordRequirements');
        if (!p1 || !p2 || !btnSave) return;

        window.togglePw = function (id) {
            var inp = document.getElementById(id);
            inp.type = inp.type === 'password' ? 'text' : 'password';
        };

        function sanitizePasswordValue(value) {
            return String(value || '').replace(/[<>"'`\\]/g, '');
        }

        function blockDangerousKeys(e) {
            var blocked = ['<', '>', '"', "'", '`', '\\'];
            if (blocked.indexOf(e.key) !== -1) {
                e.preventDefault();
            }
        }

        function normalizeText(value) {
            return String(value || '')
                .toLowerCase()
                .normalize('NFD')
                .replace(/[\u0300-\u036f]/g, '')
                .replace(/[^a-z0-9@._-]/g, '');
        }

        function getReferenceTokens() {
            var refs = [
                p1.dataset.passwordFullName || '',
                p1.dataset.passwordUsername || '',
                p1.dataset.passwordEmail || '',
            ];

            var tokens = [];
            refs.forEach(function (ref) {
                var normalized = normalizeText(ref);
                if (!normalized) return;
                tokens.push(normalized);
                if (normalized.indexOf('@') !== -1) {
                    tokens.push(normalized.split('@')[0]);
                }
            });
            return Array.from(new Set(tokens.filter(function (item) { return item.length >= 3; })));
        }

        function getCommonPasswords() {
            return [
                'password', 'password1', '12345678', '123456789', 'qwerty123',
                'admin123', 'monakeratina', 'mona1234', 'abcd1234', 'abcdef12',
                'welcome123', 'contrasena1', 'clave1234', 'nueva1234', 'mona2026'
            ];
        }

        function calcScore(v) {
            var s = 0;
            if (v.length >= 8) s++;
            if (/[A-Z]/.test(v)) s++;
            if (/[a-z]/.test(v)) s++;
            if (/[0-9]/.test(v)) s++;
            if (/[^A-Za-z0-9]/.test(v)) s++;
            return s;
        }

        function setRequirementState(rule, state) {
            if (!requirementsCard) return;
            var item = requirementsCard.querySelector('[data-rule="' + rule + '"]');
            if (!item) return;
            var icon = item.querySelector('.req-icon');
            item.classList.remove('is-pass', 'is-fail', 'is-neutral');
            item.classList.add(state === 'pass' ? 'is-pass' : state === 'fail' ? 'is-fail' : 'is-neutral');
            if (icon) {
                if (state === 'pass') {
                    icon.textContent = '\u2713';
                } else if (state === 'fail') {
                    icon.textContent = '\u2715';
                } else {
                    icon.textContent = '\u25cb';
                }
            }
        }

        function passwordChecks(v) {
            var normalized = normalizeText(v);
            var refs = getReferenceTokens();
            var hasSimilarity = refs.length ? refs.some(function (ref) { return normalized && normalized.indexOf(ref) !== -1; }) : null;
            var hasCommon = getCommonPasswords().indexOf(normalized) !== -1;

            return {
                length: v.length >= 8,
                uppercase: /[A-Z]/.test(v),
                lowercase: /[a-z]/.test(v),
                number: /[0-9]/.test(v),
                special: /[^A-Za-z0-9]/.test(v),
                similarity: hasSimilarity === null ? null : !hasSimilarity,
                common: normalized ? !hasCommon : null,
            };
        }

        function validateForm() {
            var v1 = p1.value, v2 = p2.value;
            var checks = passwordChecks(v1);
            var similarityOk = checks.similarity === null ? true : checks.similarity;
            var commonOk = checks.common === null ? true : checks.common;
            var ok = checks.length && checks.uppercase && checks.lowercase && checks.number && checks.special && similarityOk && commonOk && v2.length > 0 && v1 === v2;
            btnSave.disabled = !ok;
        }

        function checkMatch() {
            var v1 = p1.value, v2 = p2.value;
            mtxt.className = 'match-text';
            if (!v2) { mtxt.textContent = ''; validateForm(); return; }
            if (v1 === v2) {
                mtxt.textContent = '\u2713 Las contraseñas coinciden';
                mtxt.classList.add('match-ok');
            } else {
                mtxt.textContent = '\u2715 Las contraseñas no coinciden';
                mtxt.classList.add('match-fail');
            }
            validateForm();
        }

        function updateStrength() {
            var v = p1.value, score = calcScore(v);
            var cls = ['', 'weak', 'ok', 'ok', 'strong', 'strong'];
            var lbl = ['', 'Muy débil', 'Regular', 'Buena', 'Fuerte', 'Muy fuerte'];
            segs.forEach(function (s, i) { if (s) s.className = 'bar-seg ' + (i < score ? cls[Math.min(score, 5)] : ''); });
            if (stxt) stxt.innerHTML = v.length ? lbl[score] : '';

            var checks = passwordChecks(v);
            setRequirementState('length', checks.length ? 'pass' : 'fail');
            setRequirementState('uppercase', checks.uppercase ? 'pass' : 'fail');
            setRequirementState('lowercase', checks.lowercase ? 'pass' : 'fail');
            setRequirementState('number', checks.number ? 'pass' : 'fail');
            setRequirementState('special', checks.special ? 'pass' : 'fail');
            setRequirementState('similarity', checks.similarity === null ? 'neutral' : (checks.similarity ? 'pass' : 'fail'));
            setRequirementState('common', checks.common === null ? 'neutral' : (checks.common ? 'pass' : 'fail'));
            checkMatch();
        }

        p1.addEventListener('keydown', blockDangerousKeys);
        p2.addEventListener('keydown', blockDangerousKeys);
        p1.addEventListener('input', function () {
            var clean = sanitizePasswordValue(p1.value);
            if (clean !== p1.value) p1.value = clean;
            updateStrength();
        });
        p2.addEventListener('paste', function (e) {
            e.preventDefault();
        });
        p2.addEventListener('input', function () {
            var clean = sanitizePasswordValue(p2.value);
            if (clean !== p2.value) p2.value = clean;
            checkMatch();
        });
        if (window.__authRecoveryCanvasStarted !== true) {
            window.__authRecoveryCanvasStarted = true;
            startCanvas();
        }

        updateStrength();
    }
    document.addEventListener('DOMContentLoaded', function () {
        if (document.getElementById('recuperarForm')) setupRecoveryEmail();
        if (document.getElementById('codigoForm')) setupVerifyCode();
        if (document.getElementById('btnSave')) setupNewPassword();
        document.addEventListener('click', function (e) {
            var toggleBtn = e.target.closest('[data-toggle-password]');
            if (!toggleBtn) return;
            var inputId = toggleBtn.dataset.togglePassword;
            if (inputId && typeof window.togglePw === 'function') {
                window.togglePw(inputId);
            }
        });
        if (document.getElementById('leftCanvas') && !window.__authRecoveryCanvasStarted) {
            window.__authRecoveryCanvasStarted = true;
            startCanvas();
        }
    });
})();
