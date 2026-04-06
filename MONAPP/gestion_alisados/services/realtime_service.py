from urllib.parse import urlencode

from django.conf import settings
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.urls import reverse


TABLET_WS_TOKEN_SALT = "gestion_alisados.tablet.websocket"
DEFAULT_TABLET_WS_TOKEN_MAX_AGE = 3600


def build_tablet_launch_payload(request, cliente_obj, token_obj):
    return {
        "success": True,
        "message": "Proceso enviado a la tablet.",
        "process_state": token_obj.estado_proceso,
        "process_state_label": token_obj.get_estado_proceso_display(),
        "tablet_wait_url": request.build_absolute_uri(reverse("gestion_alisados:tablet_espera")),
        "tablet_process_url": request.build_absolute_uri(
            reverse("gestion_alisados:tablet_gestion_alisado", kwargs={"token": token_obj.token})
        ),
        "cliente": {
            "id": cliente_obj.id,
            "nombre": f"{cliente_obj.nombre} {cliente_obj.apellido}",
            "documento": cliente_obj.numero_documento,
        },
    }


def build_tablet_waiting_payload(request):
    return {
        "tablet_wait_url": request.build_absolute_uri(reverse("gestion_alisados:tablet_espera")),
        "tablet_estado_url": request.build_absolute_uri(reverse("gestion_alisados:tablet_espera_estado")),
    }


def _tablet_ws_signer():
    return TimestampSigner(salt=TABLET_WS_TOKEN_SALT)


def generate_tablet_ws_token(tablet_id):
    return _tablet_ws_signer().sign(str(tablet_id))


def validate_tablet_ws_token(tablet_id, signed_value, max_age=None):
    if not tablet_id or not signed_value:
        return False

    token_max_age = max_age or getattr(
        settings,
        "TABLET_WS_TOKEN_MAX_AGE_SECONDS",
        DEFAULT_TABLET_WS_TOKEN_MAX_AGE,
    )
    try:
        unsigned_value = _tablet_ws_signer().unsign(signed_value, max_age=token_max_age)
    except (BadSignature, SignatureExpired):
        return False
    return str(unsigned_value) == str(tablet_id)


def build_websocket_url(request, path, query_params=None):
    scheme = "wss" if request.is_secure() else "ws"
    query_string = ""
    if query_params:
        encoded_params = urlencode(query_params)
        if encoded_params:
            query_string = f"?{encoded_params}"
    return f"{scheme}://{request.get_host()}{path}{query_string}"


def build_tablet_websocket_url(request, tablet_id="default-tablet"):
    path = f"/ws/gestion-alisados/tablet/{tablet_id}/"
    return build_websocket_url(
        request,
        path,
        query_params={"access_token": generate_tablet_ws_token(tablet_id)},
    )
