from django.urls import path
from . import views

app_name = 'promociones'

urlpatterns = [
    path('', views.lista_promociones, name='lista'),
    path('crear/', views.crear_promocion, name='crear'),
    path('validar-nombre/', views.validar_nombre_promocion, name='validar_nombre_promocion'),
    path('editar/<uuid:pk>/', views.editar_promocion, name='editar'),
    path('eliminar/<uuid:pk>/', views.eliminar_promocion, name='eliminar'),
    path('toggle/<uuid:pk>/', views.toggle_activa, name='toggle_activa'),
]
