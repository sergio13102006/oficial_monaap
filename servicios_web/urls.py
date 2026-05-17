from django.urls import path
from . import views

app_name = 'servicios_web'

urlpatterns = [
    path('crear/', views.crear_servicio_web, name='crear_servicio_web'),
    path('lista/', views.lista_servicios_web, name='lista_servicios_web'),
    path('editar/<uuid:pk>/', views.editar_servicio_web, name='editar_servicio_web'),
    path('eliminar/<uuid:pk>/', views.eliminar_servicio_web, name='eliminar_servicio_web'),
    path('toggle-estado/<uuid:pk>/',views.cambiar_estado_servicio_web,name='toggle_estado_servicio_web'),
    path('publicos/', views.servicios_web_publicos, name='servicios_web_publicos'),
    path('validar-nombre/', views.validar_nombre_servicio_web, name='validar_nombre_servicio_web'),
]