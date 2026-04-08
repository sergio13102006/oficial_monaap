from django.urls import path

from . import views


app_name = "control_fondos"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("cuentas/", views.cuentas, name="cuentas"),
    path("cuentas/<int:pk>/", views.detalle_cuenta_view, name="detalle_cuenta"),
    path("apertura/", views.apertura, name="apertura"),
    path("movimientos/", views.movimientos, name="movimientos"),
    path("transferencias/", views.transferencias, name="transferencias"),
    path("historico/", views.historico, name="historico"),
]
