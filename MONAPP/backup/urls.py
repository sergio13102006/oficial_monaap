from django.urls import path

from . import views

app_name = "backup"

urlpatterns = [
    path("", views.backup_dashboard_view, name="dashboard"),
    path("crear/", views.crear_backup_view, name="crear"),
    path("importar/", views.importar_backup_view, name="importar"),
    path("descargar/<int:pk>/", views.descargar_backup_view, name="descargar"),
    path("restaurar/<int:pk>/", views.restaurar_backup_view, name="restaurar"),
    path("eliminar/<int:pk>/", views.eliminar_backup_view, name="eliminar"),
    path("detalle/<int:pk>/", views.detalle_backup_view, name="detalle"),
    path("configuracion/", views.configuracion_backup_view, name="configuracion"),
    path("api/info-bd/", views.info_base_datos_view, name="info_bd"),
]
