document.addEventListener("DOMContentLoaded", () => {
    window.scrollTo(0, 0);

    /* ===============================
       REVEAL TIPO LLAVE/SILUETA
    =============================== */
    const pageReveal = document.querySelector(".sq-page-reveal");
    const pageRevealCanvas = document.querySelector(".sq-page-reveal-canvas");
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let revealRunning = false;

    if (pageReveal && pageRevealCanvas && !prefersReducedMotion) {
        revealRunning = true;
        const ctx = pageRevealCanvas.getContext("2d", { alpha: true });
        if (!ctx) {
            revealRunning = false;
            pageReveal.remove();
        } else {
            const dpr = Math.max(1, window.devicePixelRatio || 1);
            const maskSrc = pageReveal.dataset.maskSrc;
            const maskImg = new Image();
            maskImg.decoding = "async";

            const resizeCanvas = () => {
                const w = window.innerWidth;
                const h = window.innerHeight;
                pageRevealCanvas.width = Math.floor(w * dpr);
                pageRevealCanvas.height = Math.floor(h * dpr);
                pageRevealCanvas.style.width = `${w}px`;
                pageRevealCanvas.style.height = `${h}px`;
                ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
            };

            const drawSolidBlack = () => {
                const w = window.innerWidth;
                const h = window.innerHeight;
                ctx.clearRect(0, 0, w, h);
                ctx.globalCompositeOperation = "source-over";
                ctx.fillStyle = "#000";
                ctx.fillRect(0, 0, w, h);
            };

            const drawFrame = (scale) => {
                const w = window.innerWidth;
                const h = window.innerHeight;
                const cx = w / 2;
                const cy = h / 2;
                const base = 120;
                const imgW = base * scale;
                const imgH = base * scale;

                ctx.clearRect(0, 0, w, h);
                ctx.globalCompositeOperation = "source-over";
                ctx.fillStyle = "#000";
                ctx.fillRect(0, 0, w, h);

                ctx.save();
                ctx.globalCompositeOperation = "destination-out";
                ctx.drawImage(maskImg, cx - imgW / 2, cy - imgH / 2, imgW, imgH);
                ctx.restore();
            };

            const runReveal = () => {
                resizeCanvas();
                drawSolidBlack();
                const duration = 1550;
                const diagonal = Math.hypot(window.innerWidth, window.innerHeight);
                const finalScale = Math.max(26, (diagonal / 120) * 1.35);
                const startScale = 0.9;
                const start = performance.now();

                drawFrame(startScale);

                const tick = (now) => {
                    const t = Math.min(1, (now - start) / duration);
                    const ease = 1 - Math.pow(1 - t, 3);
                    const scale = startScale + (finalScale - startScale) * ease;
                    drawFrame(scale);

                    if (t < 1) {
                        requestAnimationFrame(tick);
                        return;
                    }

                    revealRunning = false;
                    pageReveal.classList.add("is-hiding");
                    setTimeout(() => {
                        pageReveal.remove();
                    }, 150);
                };

                requestAnimationFrame(tick);
            };

            maskImg.onload = runReveal;
            maskImg.onerror = () => {
                revealRunning = false;
                pageReveal.remove();
            };
            maskImg.src = maskSrc;
        }
    } else if (pageReveal) {
        pageReveal.remove();
    }

    /* ===============================
       HERO FADE IN
    =============================== */
    const hero = document.querySelector(".sq-hero");
    if (hero) {
        requestAnimationFrame(() => {
            hero.classList.add("is-visible");
        });
    }

    /* =====================================================
       CONFIGURACION GENERAL CARRUSEL
    ===================================================== */
    const baseSpeed = -0.8;
    const inertia = 0.08;
    const accelerationRate = 0.04;
    const maxSpeed = 4;

    let isPaused = false;
    let velocity = baseSpeed;
    let targetVelocity = baseSpeed;
    let acceleration = 0;

    /* =====================================================
       IMAGENES DE FONDO
    ===================================================== */
    document.querySelectorAll(".sq-card").forEach((card) => {
        const bg = card.dataset.bg;
        if (bg) {
            card.style.backgroundImage = `url(${bg})`;
        }
    });

    /* =====================================================
       ELEMENTOS DEL CARRUSEL
    ===================================================== */
    const container = document.getElementById("infinite");
    const track1 = document.getElementById("track1");
    const track2 = document.getElementById("track2");

    let trackWidth = 0;
    let x1 = 0;
    let x2 = 0;
    let carouselReady = false;

    if (container && track1 && track2) {
        const recalcTracks = () => {
            trackWidth = track1.scrollWidth;
            x1 = 0;
            x2 = trackWidth;
            track1.style.transform = `translate3d(${x1}px,0,0)`;
            track2.style.transform = `translate3d(${x2}px,0,0)`;
            carouselReady = true;
        };

        recalcTracks();
        window.addEventListener("resize", recalcTracks);

        function animate() {
            if (carouselReady && !isPaused && !revealRunning) {
                targetVelocity += acceleration;
                targetVelocity = Math.max(-maxSpeed, Math.min(maxSpeed, targetVelocity));
                velocity += (targetVelocity - velocity) * inertia;

                x1 += velocity;
                x2 += velocity;

                if (velocity < 0) {
                    if (x1 <= -trackWidth) x1 = x2 + trackWidth;
                    if (x2 <= -trackWidth) x2 = x1 + trackWidth;
                } else {
                    if (x1 >= trackWidth) x1 = x2 - trackWidth;
                    if (x2 >= trackWidth) x2 = x1 - trackWidth;
                }

                track1.style.transform = `translate3d(${x1}px,0,0)`;
                track2.style.transform = `translate3d(${x2}px,0,0)`;
            }

            requestAnimationFrame(animate);
        }

        animate();

        /* =====================================================
           CONTROL POR MOUSE
        ===================================================== */
        container.addEventListener("mousemove", (e) => {
            if (isPaused) return;

            const rect = container.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const center = rect.width / 2;
            const distance = (mouseX - center) / center;

            if (Math.abs(distance) < 0.1) {
                acceleration = 0;
                targetVelocity = baseSpeed;
            } else if (distance < 0) {
                acceleration = accelerationRate;
            } else {
                acceleration = -accelerationRate;
            }
        });

        container.addEventListener("mouseleave", () => {
            if (isPaused) return;
            acceleration = 0;
            targetVelocity = baseSpeed;
        });
    } else {
        console.warn("Carrusel infinito no encontrado");
    }

    /* =====================================================
       HELPERS VIDEO
    ===================================================== */
    const cards = document.querySelectorAll(".sq-card");

    function setCarouselPaused(paused) {
        isPaused = paused;
        acceleration = 0;
        targetVelocity = paused ? 0 : baseSpeed;

        if (!paused) {
            velocity = baseSpeed;
        }
    }

    function prepareVideo(video) {
        if (!video) return;

        video.muted = true;
        video.defaultMuted = true;
        video.playsInline = true;
        video.setAttribute("muted", "");
        video.setAttribute("playsinline", "");
        video.setAttribute("webkit-playsinline", "");
        video.setAttribute("preload", "metadata");
    }

    function closeVideo(card, video, resumeCarousel = true) {
        if (!card) return;

        card.classList.remove("is-video");
        card.classList.remove("is-playing");

        if (video) {
            try {
                video.pause();
                video.currentTime = 0;
            } catch (err) {
                console.warn("No se pudo cerrar el video:", err);
            }
        }

        if (resumeCarousel) {
            setTimeout(() => {
                setCarouselPaused(false);
            }, 150);
        }
    }

    function closeAllVideos(exceptCard = null) {
        document.querySelectorAll(".sq-card.is-video").forEach((openCard) => {
            if (exceptCard && openCard === exceptCard) return;

            const openVideo = openCard.querySelector("video.sq-video");
            closeVideo(openCard, openVideo, false);
        });
    }

    async function openVideo(card, video) {
        if (!card || !video) return;

        closeAllVideos(card);
        setCarouselPaused(true);

        card.classList.add("is-video");
        prepareVideo(video);

        try {
            video.pause();
            video.currentTime = 0;
        } catch (err) {
            console.warn("No se pudo reiniciar el video:", err);
        }

        try {
            await new Promise((resolve) => setTimeout(resolve, 120));

            const playPromise = video.play();

            if (playPromise && typeof playPromise.then === "function") {
                await playPromise;
            }

            card.classList.add("is-playing");
        } catch (err) {
            console.warn("Error al reproducir video:", err);
        }
    }

    /* =====================================================
       CLICK EN CARD -> VIDEO + PAUSA
    ===================================================== */
    cards.forEach((card) => {
        const video = card.querySelector("video.sq-video");

        if (video) {
            prepareVideo(video);

            video.addEventListener("click", (e) => {
                e.stopPropagation();
            });

            video.addEventListener("ended", () => {
                closeVideo(card, video, true);
            });

            video.addEventListener("error", () => {
                console.warn("El video no pudo cargarse:", video.currentSrc || video.src);
            });

            video.addEventListener("loadeddata", () => {
                card.classList.add("video-loaded");
            });
        }

        card.addEventListener("click", async (e) => {
            const clickedVideo = e.target.closest("video");
            if (clickedVideo) return;

            if (!video) {
                closeAllVideos(null);
                setCarouselPaused(false);
                return;
            }

            if (card.classList.contains("is-video")) {
                closeVideo(card, video, true);
                return;
            }

            await openVideo(card, video);
        });
    });

    /* ===============================
       PROMOCIONES SHOWCASE
    =============================== */
    const promoStage = document.querySelector("[data-promotions-stage]");
    if (promoStage) {
        const viewport = promoStage.querySelector("[data-promotions-viewport]");
        const promoCards = Array.from(promoStage.querySelectorAll("[data-promo-card]"));
        const promoPanels = Array.from(promoStage.querySelectorAll("[data-promo-panel]"));
        const promoBgs = Array.from(promoStage.querySelectorAll("[data-promo-bg]"));
        const prevBtn = promoStage.querySelector("[data-promotions-prev]");
        const nextBtn = promoStage.querySelector("[data-promotions-next]");
        let activeIndex = 0;

        const setActivePromo = (index, shouldScroll = true) => {
            if (!promoCards.length) return;

            activeIndex = Math.max(0, Math.min(index, promoCards.length - 1));

            promoCards.forEach((card, i) => {
                card.classList.toggle("is-active", i === activeIndex);
            });

            promoPanels.forEach((panel, i) => {
                panel.classList.toggle("is-active", i === activeIndex);
            });

            promoBgs.forEach((bg, i) => {
                bg.classList.toggle("is-active", i === activeIndex);
            });

            if (prevBtn) prevBtn.disabled = activeIndex === 0;
            if (nextBtn) nextBtn.disabled = activeIndex === promoCards.length - 1;

            if (shouldScroll && viewport) {
                const target = promoCards[activeIndex];
                viewport.scrollTo({
                    left: Math.max(0, target.offsetLeft - 24),
                    behavior: "smooth",
                });
            }
        };

        promoCards.forEach((card, index) => {
            card.addEventListener("click", () => {
                setActivePromo(index);
            });
        });

        if (prevBtn) {
            prevBtn.addEventListener("click", () => {
                setActivePromo(activeIndex - 1);
            });
        }

        if (nextBtn) {
            nextBtn.addEventListener("click", () => {
                setActivePromo(activeIndex + 1);
            });
        }

        viewport?.addEventListener("scroll", () => {
            const viewportCenter = viewport.scrollLeft + viewport.clientWidth / 2;
            let closestIndex = activeIndex;
            let closestDistance = Number.POSITIVE_INFINITY;

            promoCards.forEach((card, index) => {
                const cardCenter = card.offsetLeft + card.offsetWidth / 2;
                const distance = Math.abs(cardCenter - viewportCenter);
                if (distance < closestDistance) {
                    closestDistance = distance;
                    closestIndex = index;
                }
            });

            window.requestAnimationFrame(() => {
                setActivePromo(closestIndex, false);
            });
        });

        window.addEventListener("resize", () => setActivePromo(activeIndex, false));
        setActivePromo(0, false);
    }

    /* ===============================
       CAMBIO DE FONDO POR SCROLL
    =============================== */
    const body = document.body;
        const sections = [
            { id: "infinite",    class: "bg-white" },
            { id: "productos",   class: "bg-brown" },
            { id: "contactenos", class: "bg-black" }
        ];

    function onScrollChangeBackground() {
        const mid = window.scrollY + window.innerHeight / 2;

        sections.forEach((section) => {
            const el = document.getElementById(section.id);
            if (!el) return;

            const top = el.offsetTop;
            const bottom = top + el.offsetHeight;

            if (mid >= top && mid < bottom) {
                body.classList.remove("bg-white", "bg-brown", "bg-black");
                body.classList.add(section.class);
            }
        });
    }

    window.addEventListener("scroll", onScrollChangeBackground);
    window.addEventListener("load", onScrollChangeBackground);

    /* ===============================
       GLOW SIGUIENDO EL MOUSE (CONTACTO)
    =============================== */
    const socialCards = document.querySelectorAll(".sq-social-card");

    function setCardGlowFromEvent(card, event) {
        const rect = card.getBoundingClientRect();
        const x = Math.min(Math.max(0, event.clientX - rect.left), rect.width);
        const y = Math.min(Math.max(0, event.clientY - rect.top), rect.height);

        const mx = rect.width ? (x / rect.width) * 100 : 50;
        const my = rect.height ? (y / rect.height) * 100 : 50;

        card.style.setProperty("--mx", `${mx}%`);
        card.style.setProperty("--my", `${my}%`);
    }

    socialCards.forEach((card) => {
        card.addEventListener("pointerenter", (e) => setCardGlowFromEvent(card, e));
        card.addEventListener("pointermove", (e) => setCardGlowFromEvent(card, e));
        card.addEventListener("pointerleave", () => {
            card.style.removeProperty("--mx");
            card.style.removeProperty("--my");
        });
    });

    /* ===============================
       FLIP CARD (PRODUCTOS)
    =============================== */
    const productCards = Array.from(document.querySelectorAll(".sq-product-card"));

    function setProductCardPressed(card, pressed) {
        card.setAttribute("aria-pressed", pressed ? "true" : "false");
        const backFace = card.querySelector(".sq-product-face--back");
        if (backFace) {
            backFace.setAttribute("aria-hidden", pressed ? "false" : "true");
        }
    }

    function closeAllProductCards(except = null) {
        productCards.forEach((card) => {
            if (except && card === except) return;
            if (!card.classList.contains("is-flipped")) return;
            card.classList.remove("is-flipped");
            setProductCardPressed(card, false);
        });
    }

    productCards.forEach((card) => {
        setProductCardPressed(card, false);

        card.addEventListener("click", (e) => {
            if (e.target.closest("a, button")) return;

            const willFlip = !card.classList.contains("is-flipped");
            closeAllProductCards(card);
            card.classList.toggle("is-flipped", willFlip);
            setProductCardPressed(card, willFlip);
        });

        card.addEventListener("keydown", (e) => {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                card.click();
            }

            if (e.key === "Escape") {
                if (!card.classList.contains("is-flipped")) return;
                card.classList.remove("is-flipped");
                setProductCardPressed(card, false);
            }
        });
    });

    document.addEventListener("click", (e) => {
        const anyFlipped = productCards.some((card) => card.classList.contains("is-flipped"));
        if (!anyFlipped) return;

        const clickedCard = e.target.closest(".sq-product-card");
        if (clickedCard) return;

        closeAllProductCards(null);
    });
/* ===============================
   ANIMACIONES AL SCROLL (FADE UP)
=============================== */
const fadeUpElements = document.querySelectorAll(
    ".sq-intro-content, .sq-intro-media, .sq-section-head, " +
    ".sq-product-card, .sq-social-card, .sq-contact-header, " +
    ".sq-promo-card-mini, .sq-products-title, .sq-services-heading, " +
    ".sq-promo-feature.is-active, .sq-promotions-head--inside, " +
    ".footer-info-block, .footer-map, .mona-footer .footer-logo, .mona-footer .copyright, " +
    ".sq-card"
);

fadeUpElements.forEach(el => el.classList.add("sq-fade-up"));

function checkFadeElements() {
    const windowHeight = window.innerHeight;

    fadeUpElements.forEach(el => {
        const rect = el.getBoundingClientRect();
        const elementTop = rect.top;
        const elementBottom = rect.bottom;

        /* Excepción para elementos dentro de overflow:hidden del carrusel */
        const insideTrack = el.closest(".sq-tracks-wrapper");
        if (insideTrack) {
            const parentRect = insideTrack.getBoundingClientRect();
            const isParentVisible = parentRect.top < windowHeight && parentRect.bottom > 0;
            if (isParentVisible) {
                el.classList.add("is-visible");
            } else {
                el.classList.remove("is-visible");
            }
            return;
        }

        /* Excepción para elementos dentro del stage de promociones */
        const insideStage = el.closest(".sq-promotions-stage");
        if (insideStage) {
            const parentRect = insideStage.getBoundingClientRect();
            const isParentVisible = parentRect.top < windowHeight && parentRect.bottom > 0;
            if (isParentVisible) {
                el.classList.add("is-visible");
            } else {
                el.classList.remove("is-visible");
            }
            return;
        }

        const isVisible = elementTop < windowHeight * 0.88 && elementBottom > 0;
        if (isVisible) {
            el.classList.add("is-visible");
        } else {
            el.classList.remove("is-visible");
        }
    });

    /* Fuerza visibilidad del copyright y divider siempre */
    document.querySelectorAll(".mona-footer .copyright, .footer-divider").forEach(el => {
        el.classList.add("is-visible");
    });
}

window.addEventListener("scroll", checkFadeElements, { passive: true });
window.addEventListener("resize", checkFadeElements, { passive: true });
checkFadeElements();
});
