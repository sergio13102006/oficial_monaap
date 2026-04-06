from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(
        r"ws/gestion-alisados/tablet/(?P<tablet_id>[-\w]+)/$",
        consumers.TabletConsumer.as_asgi(),
        name="ws_tablet",
    ),
    re_path(
        r"ws/gestion-alisados/admin/$",
        consumers.AdminConsumer.as_asgi(),
        name="ws_admin",
    ),
]
