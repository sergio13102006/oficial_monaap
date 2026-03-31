from django.urls import path
from . import views

app_name = 'productos_web'

urlpatterns = [
    path('', views.lista_productos_web, name='lista'),
    path('crear/', views.crear_producto_web, name='crear'),
    path('validar-nombre/', views.validar_nombre_producto_web, name='validar_nombre_producto_web'),
    path('api/detalle/<uuid:pk>/', views.detalle_producto_web_json, name='detalle_json'),
    path('editar/<uuid:pk>/', views.editar_producto_web, name='editar'),
    path('eliminar/<uuid:pk>/', views.eliminar_producto_web, name='eliminar'),
    path('toggle/<uuid:pk>/', views.toggle_visible, name='toggle_visible'),
]
