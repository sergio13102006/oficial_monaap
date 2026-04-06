from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from ..forms import GestionAlisadoForm
from ..models import TabletConsentToken, TabletKioskState
from .admin_service import _promociones_activas
from .persistence_service import get_last_gestion_values
from .realtime_notifications import (
    notify_back_to_waiting,
    notify_save_error,
    notify_session_assigned,
    notify_session_cancelled,
    notify_session_opened,
)


def start_tablet_session(cliente_obj, user=None, minutos_validos=120):
    for token in TabletConsentToken.objects.filter(activo=True, usado_en__isnull=True):
        token.marcar_estado(
            TabletConsentToken.ESTADO_CANCELADA,
            activo=False,
            detalle='Sesion reemplazada por una nueva captura.',
        )
        notify_session_cancelled('default-tablet', str(token.token), payload={"detail": token.detalle_estado})

    token = TabletConsentToken.objects.create(
        cliente=cliente_obj,
        creado_por=user if getattr(user, "is_authenticated", False) else None,
        expira_en=timezone.now() + timedelta(minutes=minutos_validos),
        estado_proceso=TabletConsentToken.ESTADO_ENVIADA,
        detalle_estado='Sesion enviada a la tablet y pendiente de apertura.',
    )
    notify_session_assigned(
        'default-tablet',
        str(token.token),
        payload={
            "cliente_id": cliente_obj.id,
            "cliente_nombre": f"{cliente_obj.nombre} {cliente_obj.apellido}",
            "cliente_documento": cliente_obj.numero_documento,
            "tablet_process_url": reverse("gestion_alisados:tablet_gestion_alisado", kwargs={"token": token.token}),
        },
    )
    return token


def get_kiosk_state():
    state, _ = TabletKioskState.objects.get_or_create(
        pk=TabletKioskState.SINGLETON_ID,
        defaults={"estado": TabletKioskState.ESTADO_ESPERA},
    )
    if state.estado != TabletKioskState.ESTADO_LISTO and (
        state.token_id is not None or state.cliente_id is not None or state.gestion_id is not None
    ):
        state.marcar_espera()
    return state


def mark_kiosk_waiting():
    state = get_kiosk_state()
    if (
        state.estado != TabletKioskState.ESTADO_ESPERA
        or state.token_id is not None
        or state.cliente_id is not None
        or state.gestion_id is not None
    ):
        state.marcar_espera()
    return state


def mark_kiosk_ready(cliente_obj, token_obj, gestion=None):
    state = get_kiosk_state()
    state.marcar_listo(cliente_obj, token_obj, gestion=gestion)
    return state


def mark_kiosk_connection(tablet_id, connected):
    state = get_kiosk_state()
    if connected:
        state.marcar_conectada(tablet_id=tablet_id)
    else:
        state.marcar_desconectada()
    return state


def touch_kiosk_activity(tablet_id=None):
    state = get_kiosk_state()
    if tablet_id and state.tablet_id != tablet_id:
        state.tablet_id = tablet_id
        state.save(update_fields=["tablet_id", "actualizado_en"])
    state.touch_actividad()
    return state


def build_tablet_capture_context(token_obj):
    cliente_obj = token_obj.cliente
    form = GestionAlisadoForm(initial=get_last_gestion_values(cliente_obj) if cliente_obj else None)
    form.fields["cliente"].widget.attrs["id"] = "selectCliente"
    form.fields["cliente"].widget.attrs["class"] = "form-select"
    form.fields["cliente"].widget.attrs["disabled"] = "disabled"
    return {
        "form": form,
        "is_modal": False,
        "tablet_mode": True,
        "cliente_preseleccionado": cliente_obj,
        "cliente_bloqueado": True,
        "cliente_id_bloqueado": cliente_obj.id if cliente_obj else "",
        "desde_clientes": False,
        "promociones_activas": _promociones_activas(),
        "tablet_token": token_obj,
    }


def build_invalid_tablet_context(message, tablet_wait_url):
    return {
        "message": message,
        "tablet_wait_url": tablet_wait_url,
    }


def sync_token_process_state(token_obj):
    if token_obj.usado_en:
        if token_obj.estado_proceso != TabletConsentToken.ESTADO_FIRMADA:
            token_obj.marcar_estado(
                TabletConsentToken.ESTADO_FIRMADA,
                activo=False,
                detalle='Consentimiento firmado correctamente.',
                usado_en=token_obj.usado_en,
            )
        return token_obj

    if token_obj.expira_en <= timezone.now():
        if token_obj.estado_proceso != TabletConsentToken.ESTADO_EXPIRADA:
            token_obj.marcar_estado(
                TabletConsentToken.ESTADO_EXPIRADA,
                activo=False,
                detalle='La sesion expiro antes de completar la firma.',
            )
        return token_obj

    return token_obj


def mark_tablet_session_opened(token_obj):
    sync_token_process_state(token_obj)
    if token_obj.estado_proceso in {
        TabletConsentToken.ESTADO_FIRMADA,
        TabletConsentToken.ESTADO_CANCELADA,
        TabletConsentToken.ESTADO_EXPIRADA,
    }:
        return token_obj

    abierta_en = token_obj.abierta_en or timezone.now()
    token_obj.marcar_estado(
        TabletConsentToken.ESTADO_ABIERTA,
        activo=True,
        detalle='La sesion fue abierta en la tablet.',
        abierta_en=abierta_en,
    )
    notify_session_opened('default-tablet', str(token_obj.token), payload={"opened_at": abierta_en.isoformat()})
    return token_obj


def mark_tablet_session_error(token_obj, detalle):
    token_obj.marcar_estado(
        TabletConsentToken.ESTADO_ERROR,
        activo=False,
        detalle=detalle,
    )
    notify_save_error('default-tablet', str(token_obj.token), payload={"detail": detalle})
    return token_obj
