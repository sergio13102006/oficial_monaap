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
    path("cierre/", views.cierre, name="cierre"),
    path("reabrir/", views.reabrir, name="reabrir"),
    path("historico/", views.historico, name="historico"),
    path("bitacora/", views.bitacora, name="bitacora"),
    path("exportar/movimientos.xlsx", views.exportar_movimientos_excel, name="exportar_movimientos_excel"),
    path("exportar/cierre.xlsx", views.exportar_cierre_excel, name="exportar_cierre_excel"),
    path("exportar/bitacora.xlsx", views.exportar_bitacora_excel, name="exportar_bitacora_excel"),
    path("exportar/movimientos.csv", views.exportar_movimientos_excel, name="exportar_movimientos_csv"),
    path("exportar/cierre.csv", views.exportar_cierre_excel, name="exportar_cierre_csv"),
    path("exportar/bitacora.csv", views.exportar_bitacora_excel, name="exportar_bitacora_csv"),
]
