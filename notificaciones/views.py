from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.timesince import timesince
from django.utils import timezone
import re
from .models import Notificacion
from .alertas_diarias import generar_alertas_para_usuario


def _es_admin_o_auxiliar(user):
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=['Administrador', 'Auxiliar']).exists()


# ─── GET /notificaciones/listar/ ─────────────────────────────────────────────
@login_required
def listar_notificaciones(request):
    if not _es_admin_o_auxiliar(request.user):
        return JsonResponse({'permitido': False, 'notificaciones': [], 'total': 0, 'urgentes': 0})

    # Generar alertas al abrir la campana (idempotente por usuario)
    try:
        generar_alertas_para_usuario(request.user)
    except Exception:
        # No bloquear el panel si falla la generación de alertas
        pass

    notifs = Notificacion.objects.filter(
        destinatario=request.user,
        leida=False,
    ).order_by('-urgente', '-fecha_creacion')[:20]

    def _mensaje_publico(msg: str) -> str:
        if not msg:
            return ""
        # Ocultar marcadores internos usados para idempotencia (no mostrar al usuario)
        msg = re.sub(r"\\s*\\[#(?:PROMO_VENCE|CUMPLE):[^\\]]+\\]", "", msg).strip()
        msg = re.sub(r"\\s*#(?:PROMO_VENCE|CUMPLE):\\S+", "", msg).strip()
        return msg

    data = []
    for n in notifs:
        data.append({
            'id':      n.id,
            'titulo':  n.titulo,
            'mensaje': _mensaje_publico(n.mensaje),
            'tipo':    n.tipo,
            'urgente': n.urgente,
            'icono':   n.icono,
            'color':   n.color_icono,
            'hace':    timesince(n.fecha_creacion, timezone.now()),
        })

    urgentes = sum(1 for n in data if n['urgente'])

    return JsonResponse({
        'permitido':      True,
        'notificaciones': data,
        'total':          len(data),
        'urgentes':       urgentes,
    })


# ─── POST /notificaciones/<id>/leer/ ─────────────────────────────────────────
@login_required
@require_POST
def marcar_leida(request, notif_id):
    if not _es_admin_o_auxiliar(request.user):
        return JsonResponse({'success': False}, status=403)
    try:
        n = Notificacion.objects.get(id=notif_id, destinatario=request.user)
        n.leida = True
        n.save(update_fields=['leida'])
        return JsonResponse({'success': True})
    except Notificacion.DoesNotExist:
        return JsonResponse({'success': False}, status=404)


# ─── POST /notificaciones/leer-todas/ ────────────────────────────────────────
@login_required
@require_POST
def marcar_todas_leidas(request):
    if not _es_admin_o_auxiliar(request.user):
        return JsonResponse({'success': False}, status=403)

    Notificacion.objects.filter(
        destinatario=request.user,
        leida=False,
    ).update(leida=True)

    return JsonResponse({'success': True})
