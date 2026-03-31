from django.urls import path
from . import views

app_name = 'proveedores'

urlpatterns = [
    path('', views.lista_proveedores, name='lista_proveedor'),
    path('crear/', views.crear_proveedor, name='crear_proveedor'),
    path('validar-nombre/', views.validar_nombre_proveedor, name='validar_nombre_proveedor'),
    path('editar/<int:pk>/', views.editar_proveedor, name='editar_proveedor'),
    path('eliminar/<int:pk>/', views.eliminar_proveedor, name='eliminar_proveedor'),
    path('desactivar/<int:pk>/', views.desactivar_proveedor, name='desactivar'),
    path('reactivar/<int:pk>/', views.reactivar_proveedor, name='reactivar'),
]
