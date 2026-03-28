from django.urls import path
from . import views

app_name = 'productos'

urlpatterns = [
    path('', views.lista_productos, name='lista_productos'),
    path('crear/', views.crear_producto, name='crear_producto'),
    path('<int:codigo>/editar/', views.editar_producto, name='editar_producto'),
    path('<str:codigo>/eliminar/', views.eliminar_producto, name='eliminar_producto'),
    path('<int:codigo>/toggle-activo/', views.toggle_activo_producto, name='toggle_activo_producto'),
    path('<int:id>/detalle/', views.detalle_compra_json, name='detalle_compra_json'),
    path('validar-nombre/', views.validar_nombre_producto, name='validar_nombre_producto'),
]
