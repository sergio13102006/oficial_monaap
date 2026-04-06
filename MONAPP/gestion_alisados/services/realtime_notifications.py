import uuid
import logging
from datetime import datetime, timezone

from asgiref.sync import async_to_sync
from django.conf import settings

try:
    from channels.layers import get_channel_layer
except Exception:  # pragma: no cover - channels may be absent locally
    get_channel_layer = None


ADMIN_GROUP = "gestion_alisados.admin"
EVENT_CONTRACT_VERSION = 1
logger = logging.getLogger(__name__)


def get_realtime_enabled():
    return bool(getattr(settings, "ENABLE_CHANNELS", False) and get_channel_layer is not None)


def build_tablet_group_name(tablet_id):
    return f"gestion_alisados.tablet.{tablet_id}"


def build_session_group_name(session_id):
    return f"gestion_alisados.session.{session_id}"


def build_runtime_event(event_type, *, tablet_id=None, session_id=None, status="", payload=None, source="backend"):
    payload = payload if isinstance(payload, dict) else {}
    event_id = str(uuid.uuid4())
    return {
        "type": event_type,
        "event_id": event_id,
        "message_id": event_id,
        "contract_version": EVENT_CONTRACT_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tablet_id": tablet_id,
        "session_id": session_id,
        "status": status,
        "payload": payload,
        "source": source,
    }


def _base_event(event_type, *, tablet_id=None, session_id=None, status="", payload=None, source="backend"):
    return build_runtime_event(
        event_type,
        tablet_id=tablet_id,
        session_id=session_id,
        status=status,
        payload=payload,
        source=source,
    )


def _send_to_group(group_name, handler_type, event):
    if not get_realtime_enabled():
        logger.debug("Realtime disabled, skipping event %s for group %s", event.get("type"), group_name)
        return False

    channel_layer = get_channel_layer()
    if channel_layer is None:
        logger.warning("Channel layer unavailable for realtime event %s", event.get("type"))
        return False

    try:
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": handler_type,
                "event": event,
            },
        )
    except Exception:
        logger.exception(
            "Failed to send realtime event %s to group %s",
            event.get("type"),
            group_name,
        )
        return False
    logger.info(
        "Realtime event %s sent to %s with session=%s tablet=%s",
        event.get("type"),
        group_name,
        event.get("session_id"),
        event.get("tablet_id"),
    )
    return True


def notify_tablet_connected(tablet_id, payload=None):
    event = _base_event(
        "tablet_connected",
        tablet_id=tablet_id,
        status="connected",
        payload=payload,
        source="realtime_service",
    )
    return _send_to_group(ADMIN_GROUP, "tablet.connected", event)


def notify_session_assigned(tablet_id, session_id, payload=None):
    event = _base_event(
        "session_assigned",
        tablet_id=tablet_id,
        session_id=session_id,
        status="enviada_a_tablet",
        payload=payload,
        source="business_action",
    )
    sent = _send_to_group(build_tablet_group_name(tablet_id), "session.assigned", event)
    _send_to_group(build_session_group_name(session_id), "session.assigned", event)
    return sent


def notify_session_opened(tablet_id, session_id, payload=None):
    event = _base_event(
        "session_opened",
        tablet_id=tablet_id,
        session_id=session_id,
        status="abierta_en_tablet",
        payload=payload,
        source="tablet_consumer",
    )
    sent = _send_to_group(ADMIN_GROUP, "session.opened", event)
    _send_to_group(build_session_group_name(session_id), "session.opened", event)
    return sent


def notify_signature_completed(tablet_id, session_id, payload=None):
    event = _base_event(
        "signature_completed",
        tablet_id=tablet_id,
        session_id=session_id,
        status="firmada",
        payload=payload,
        source="business_action",
    )
    sent = _send_to_group(ADMIN_GROUP, "signature.completed", event)
    _send_to_group(build_session_group_name(session_id), "signature.completed", event)
    return sent


def notify_save_error(tablet_id, session_id, payload=None):
    event = _base_event(
        "save_error",
        tablet_id=tablet_id,
        session_id=session_id,
        status="error",
        payload=payload,
        source="business_action",
    )
    sent = _send_to_group(ADMIN_GROUP, "save.error", event)
    _send_to_group(build_session_group_name(session_id), "save.error", event)
    return sent


def notify_session_cancelled(tablet_id, session_id, payload=None):
    event = _base_event(
        "session_cancelled",
        tablet_id=tablet_id,
        session_id=session_id,
        status="cancelada",
        payload=payload,
        source="business_action",
    )
    sent = _send_to_group(build_tablet_group_name(tablet_id), "session.cancelled", event)
    _send_to_group(build_session_group_name(session_id), "session.cancelled", event)
    return sent


def notify_back_to_waiting(tablet_id, session_id=None, payload=None):
    event = _base_event(
        "back_to_waiting",
        tablet_id=tablet_id,
        session_id=session_id,
        status="pendiente",
        payload=payload,
        source="business_action",
    )
    sent = _send_to_group(build_tablet_group_name(tablet_id), "back.to.waiting", event)
    if session_id:
        _send_to_group(build_session_group_name(session_id), "back.to.waiting", event)
    return sent


def notify_reconnect_required(tablet_id, session_id=None, payload=None):
    event = _base_event(
        "reconnect_required",
        tablet_id=tablet_id,
        session_id=session_id,
        status="reconnect_required",
        payload=payload,
        source="backend",
    )
    sent = _send_to_group(build_tablet_group_name(tablet_id), "reconnect.required", event)
    if session_id:
        _send_to_group(build_session_group_name(session_id), "reconnect.required", event)
    return sent
