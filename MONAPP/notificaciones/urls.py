from django.urls import path
from . import views

app_name = 'notificaciones'

urlpatterns = [
    # Listar notificaciones no leídas (GET → JSON)
    path('listar/',               views.listar_notificaciones, name='listar'),

    # Marcar una como leída (POST → JSON)
    path('<int:notif_id>/leer/',  views.marcar_leida,          name='marcar_leida'),

    # Marcar todas como leídas (POST → JSON)
    path('leer-todas/',           views.marcar_todas_leidas,   name='marcar_todas_leidas'),
]

# ── En tu urls.py principal agrega: ──────────────────────────────────────────
#
#   from django.urls import path, include
#
#   urlpatterns = [
#       ...
#       path('notificaciones/', include('notificaciones.urls')),
#       ...
#   ]
#
# ── Notificación de prueba (ejecutar en shell o migration) ───────────────────
#
#   from django.contrib.auth.models import User
#   from notificaciones.models import Notificacion
#
#   admin = User.objects.filter(groups__name='Administrador').first()
#   Notificacion.objects.create(
#       destinatario = admin,
#       titulo   = '¡Bienvenido al sistema!',
#       mensaje  = 'Esta es tu primera notificación de prueba. Todo funciona correctamente.',
#       tipo     = 'success',
#   )