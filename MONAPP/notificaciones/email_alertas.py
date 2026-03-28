# notificaciones/email_alertas.py
#
# Envío de alertas por correo electrónico usando Gmail SMTP.
# Django ya incluye soporte nativo — sin instalar nada extra.
#
# ══════════════════════════════════════════════════════════════
#  CONFIGURACIÓN en settings.py (agregar estas líneas):
#
#  EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
#  EMAIL_HOST          = 'smtp.gmail.com'
#  EMAIL_PORT          = 587
#  EMAIL_USE_TLS       = True
#  EMAIL_HOST_USER     = 'tucorreo@gmail.com'       ← tu Gmail
#  EMAIL_HOST_PASSWORD = 'xxxx xxxx xxxx xxxx'      ← contraseña de app
#  DEFAULT_FROM_EMAIL  = 'MONAPP <tucorreo@gmail.com>'
#
#  Para obtener la contraseña de app de Gmail:
#  1. Entra a myaccount.google.com
#  2. Seguridad → Verificación en 2 pasos (actívala si no está)
#  3. Seguridad → Contraseñas de aplicaciones
#  4. Selecciona "Correo" y "Windows/Mac" → Generar
#  5. Copia los 16 caracteres que aparecen (con espacios)
# ══════════════════════════════════════════════════════════════

import logging
import threading

from django.core.mail import EmailMultiAlternatives
from django.conf import settings

logger = logging.getLogger(__name__)


def _construir_html_stock_cero(nombre):
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head><meta charset="UTF-8"></head>
    <body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr><td align="center" style="padding:30px 20px;">
          <table width="580" cellpadding="0" cellspacing="0"
                 style="background:#fff;border-radius:12px;overflow:hidden;
                        box-shadow:0 4px 20px rgba(0,0,0,.1);">

            <!-- Cabecera roja urgente -->
            <tr>
              <td style="background:linear-gradient(135deg,#c0392b,#e74c3c);
                         padding:28px 32px;text-align:center;">
                <h1 style="margin:0;color:#fff;font-size:22px;font-weight:700;
                           letter-spacing:1px;">
                  🚨 ALERTA URGENTE — SIN STOCK
                </h1>
                <p style="margin:8px 0 0;color:rgba(255,255,255,.85);font-size:14px;">
                  Sistema MONAPP · Mona Keratina
                </p>
              </td>
            </tr>

            <!-- Cuerpo -->
            <tr>
              <td style="padding:32px;">
                <p style="margin:0 0 16px;font-size:15px;color:#444;line-height:1.6;">
                  El siguiente producto ha llegado a <strong>0 unidades</strong>
                  en el inventario:
                </p>

                <!-- Producto destacado -->
                <div style="background:#fdf2f2;border:2px solid #e74c3c;
                            border-radius:8px;padding:20px;text-align:center;
                            margin:20px 0;">
                  <p style="margin:0 0 6px;font-size:13px;color:#e74c3c;
                             font-weight:700;text-transform:uppercase;
                             letter-spacing:1px;">Producto sin stock</p>
                  <h2 style="margin:0;font-size:26px;color:#2b1a14;font-weight:800;">
                    {nombre}
                  </h2>
                  <p style="margin:10px 0 0;font-size:28px;font-weight:900;
                             color:#e74c3c;">0 unidades</p>
                </div>

                <p style="margin:16px 0;font-size:15px;color:#444;line-height:1.6;">
                  ⚠️ Es necesario realizar una <strong>compra urgente</strong>
                  para evitar quiebres de inventario y afectación al servicio.
                </p>

                <!-- Acción sugerida -->
                <div style="background:#fef9e7;border-left:4px solid #f39c12;
                            padding:16px 20px;border-radius:0 8px 8px 0;margin:20px 0;">
                  <p style="margin:0;font-size:14px;color:#7d6608;">
                    <strong>Acción recomendada:</strong> Ingresa al módulo de
                    <em>Compras</em> en el panel administrativo y genera una
                    orden de compra para este producto.
                  </p>
                </div>
              </td>
            </tr>

            <!-- Footer -->
            <tr>
              <td style="background:#f8f4f2;padding:20px 32px;
                         border-top:1px solid #e8e0d8;text-align:center;">
                <p style="margin:0;font-size:12px;color:#9a8888;">
                  Este mensaje fue generado automáticamente por
                  <strong>MONAPP · Mona Keratina</strong>.<br>
                  No respondas a este correo.
                </p>
              </td>
            </tr>

          </table>
        </td></tr>
      </table>
    </body>
    </html>
    """


def _construir_html_stock_bajo(nombre, cantidad):
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head><meta charset="UTF-8"></head>
    <body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr><td align="center" style="padding:30px 20px;">
          <table width="580" cellpadding="0" cellspacing="0"
                 style="background:#fff;border-radius:12px;overflow:hidden;
                        box-shadow:0 4px 20px rgba(0,0,0,.1);">

            <!-- Cabecera naranja warning -->
            <tr>
              <td style="background:linear-gradient(135deg,#d68910,#f39c12);
                         padding:28px 32px;text-align:center;">
                <h1 style="margin:0;color:#fff;font-size:22px;font-weight:700;
                           letter-spacing:1px;">
                  ⚠️ AVISO — STOCK BAJO
                </h1>
                <p style="margin:8px 0 0;color:rgba(255,255,255,.85);font-size:14px;">
                  Sistema MONAPP · Mona Keratina
                </p>
              </td>
            </tr>

            <!-- Cuerpo -->
            <tr>
              <td style="padding:32px;">
                <p style="margin:0 0 16px;font-size:15px;color:#444;line-height:1.6;">
                  El siguiente producto tiene pocas unidades disponibles:
                </p>

                <!-- Producto destacado -->
                <div style="background:#fef9e7;border:2px solid #f39c12;
                            border-radius:8px;padding:20px;text-align:center;
                            margin:20px 0;">
                  <p style="margin:0 0 6px;font-size:13px;color:#d68910;
                             font-weight:700;text-transform:uppercase;
                             letter-spacing:1px;">Producto con stock bajo</p>
                  <h2 style="margin:0;font-size:26px;color:#2b1a14;font-weight:800;">
                    {nombre}
                  </h2>
                  <p style="margin:10px 0 0;font-size:28px;font-weight:900;
                             color:#f39c12;">
                    {cantidad} unidad{"es" if cantidad != 1 else ""} disponible{"s" if cantidad != 1 else ""}
                  </p>
                </div>

                <p style="margin:16px 0;font-size:15px;color:#444;line-height:1.6;">
                  Se recomienda reabastecer pronto para evitar quedarse sin stock.
                </p>
              </td>
            </tr>

            <!-- Footer -->
            <tr>
              <td style="background:#f8f4f2;padding:20px 32px;
                         border-top:1px solid #e8e0d8;text-align:center;">
                <p style="margin:0;font-size:12px;color:#9a8888;">
                  Este mensaje fue generado automáticamente por
                  <strong>MONAPP · Mona Keratina</strong>.<br>
                  No respondas a este correo.
                </p>
              </td>
            </tr>

          </table>
        </td></tr>
      </table>
    </body>
    </html>
    """


def _construir_html_bienvenida(nombre, rol, username):
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head><meta charset="UTF-8"></head>
    <body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr><td align="center" style="padding:30px 20px;">
          <table width="580" cellpadding="0" cellspacing="0"
                 style="background:#fff;border-radius:12px;overflow:hidden;
                        box-shadow:0 4px 20px rgba(0,0,0,.1);">

            <!-- Cabecera café -->
            <tr>
              <td style="background:linear-gradient(135deg,#3a2a24,#5a3e2e);
                         padding:32px;text-align:center;">
                <h1 style="margin:0;color:#f5f0e8;font-size:24px;font-weight:700;">
                  👋 ¡Bienvenido/a, {nombre}!
                </h1>
                <p style="margin:10px 0 0;color:rgba(245,240,232,.75);font-size:14px;">
                  Tu cuenta ha sido creada exitosamente
                </p>
              </td>
            </tr>

            <!-- Cuerpo -->
            <tr>
              <td style="padding:32px;">
                <p style="margin:0 0 20px;font-size:15px;color:#444;line-height:1.6;">
                  Hola <strong>{nombre}</strong>, tu cuenta en
                  <strong>MONAPP · Mona Keratina</strong> ha sido activada.
                  Aquí están tus datos de acceso:
                </p>

                <div style="background:#f8f4f2;border-radius:8px;padding:20px;margin:0 0 20px;">
                  <table width="100%" cellpadding="6">
                    <tr>
                      <td style="font-size:13px;color:#9a8888;width:120px;">Rol</td>
                      <td style="font-size:14px;color:#2b1a14;font-weight:700;">{rol}</td>
                    </tr>
                    <tr>
                      <td style="font-size:13px;color:#9a8888;">Usuario</td>
                      <td style="font-size:14px;color:#2b1a14;font-weight:700;">{username}</td>
                    </tr>
                  </table>
                </div>

                <p style="margin:0;font-size:14px;color:#666;line-height:1.6;">
                  A partir de ahora recibirás alertas importantes por este correo,
                  como avisos de productos sin stock o con stock bajo.
                </p>
              </td>
            </tr>

            <!-- Footer -->
            <tr>
              <td style="background:#f8f4f2;padding:20px 32px;
                         border-top:1px solid #e8e0d8;text-align:center;">
                <p style="margin:0;font-size:12px;color:#9a8888;">
                  Este mensaje fue generado automáticamente por
                  <strong>MONAPP · Mona Keratina</strong>.<br>
                  No respondas a este correo.
                </p>
              </td>
            </tr>

          </table>
        </td></tr>
      </table>
    </body>
    </html>
    """


def _enviar(destinatarios_email, asunto, texto_plano, html):
    """Envía el email en un hilo separado para no bloquear el flujo."""
    def _worker():
        try:
            msg = EmailMultiAlternatives(
                subject=asunto,
                body=texto_plano,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=destinatarios_email,
            )
            msg.attach_alternative(html, 'text/html')
            msg.send(fail_silently=False)
            logger.info(f'Email enviado a {destinatarios_email}: {asunto}')
        except Exception as e:
            logger.error(f'Error enviando email a {destinatarios_email}: {e}')

    threading.Thread(target=_worker, daemon=True).start()


# ── API pública ───────────────────────────────────────────────────────────────

def enviar_alerta_stock_cero(nombre, emails):
    """Envía alerta roja urgente de stock en 0."""
    if not emails:
        return
    _enviar(
        destinatarios_email=emails,
        asunto=f'🚨 URGENTE: Sin stock — {nombre} | MONAPP',
        texto_plano=(
            f'ALERTA URGENTE\n\n'
            f'El producto "{nombre}" ha llegado a 0 unidades.\n'
            f'Es necesario realizar una compra urgente.\n\n'
            f'Sistema MONAPP — Mona Keratina'
        ),
        html=_construir_html_stock_cero(nombre),
    )


def enviar_alerta_stock_bajo(nombre, cantidad, emails):
    """Envía aviso amarillo de stock bajo."""
    if not emails:
        return
    _enviar(
        destinatarios_email=emails,
        asunto=f'⚠️ Stock bajo: {nombre} ({cantidad} uds.) | MONAPP',
        texto_plano=(
            f'AVISO DE STOCK BAJO\n\n'
            f'El producto "{nombre}" tiene solo {cantidad} unidades disponibles.\n'
            f'Se recomienda reabastecer pronto.\n\n'
            f'Sistema MONAPP — Mona Keratina'
        ),
        html=_construir_html_stock_bajo(nombre, cantidad),
    )


def enviar_bienvenida(nombre, rol, username, email):
    """Envía correo de bienvenida al crear un usuario Admin o Auxiliar."""
    if not email:
        return
    _enviar(
        destinatarios_email=[email],
        asunto=f'👋 Bienvenido/a a MONAPP, {nombre}',
        texto_plano=(
            f'Hola {nombre},\n\n'
            f'Tu cuenta en MONAPP ha sido creada exitosamente.\n'
            f'Rol: {rol}\n'
            f'Usuario: {username}\n\n'
            f'Sistema MONAPP — Mona Keratina'
        ),
        html=_construir_html_bienvenida(nombre, rol, username),
    )