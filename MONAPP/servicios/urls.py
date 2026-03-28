from django.urls import path
from . import views

app_name = 'servicios'

urlpatterns = [
    # URLs para Servicios
    path('', views.lista_servicios, name='lista_servicios'),
    path('crear/', views.crear_servicio, name='crear_servicio'),
    path('validar-nombre/', views.validar_nombre_servicio, name='validar_nombre_servicio'),
    path('editar/<uuid:pk>/', views.editar_servicio, name='editar_servicio'),
    path('eliminar/<uuid:pk>/', views.eliminar_servicio, name='eliminar_servicio'),
    path('publicos/', views.servicios_publicos, name='servicios_publicos'),
    path('toggle-activo/<uuid:pk>/', views.toggle_activo_servicio, name='toggle_activo_servicio'),  
]
