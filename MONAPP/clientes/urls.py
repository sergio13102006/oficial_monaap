from django.urls import path
from . import views

app_name = 'clientes'
urlpatterns = [
    path('', views.lista_clientes, name='lista'),
    path('crear/', views.crear_cliente, name='crear'),
    path('validar-documento/', views.validar_documento, name='validar_documento'),
    path('editar/<int:cliente_id>/', views.editar_cliente, name='editar'),
    path('eliminar/<int:cliente_id>/', views.eliminar_cliente, name='eliminar'),
    path('cambiar-estado/<int:cliente_id>/', views.cambiar_estado_cliente, name='cambiar_estado'),
]