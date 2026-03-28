from django.urls import path
from . import views

app_name = 'backup'

urlpatterns = [
    path('', views.backup_dashboard, name='dashboard'),
    path('crear/', views.crear_backup, name='crear'),
    path('importar/', views.importar_backup_view, name='importar'),
    path('descargar/<int:pk>/', views.descargar_backup, name='descargar'),
    path('restaurar/<int:pk>/', views.restaurar_backup_view, name='restaurar'),
    path('eliminar/<int:pk>/', views.eliminar_backup, name='eliminar'),
    path('detalle/<int:pk>/', views.detalle_backup, name='detalle'),
    path('configuracion/', views.configuracion_backup, name='configuracion'),
    path('api/info-bd/', views.info_base_datos, name='info_bd'),
]
