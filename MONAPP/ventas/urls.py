from django.urls import path
from . import views

app_name = 'ventas'

urlpatterns = [
    path('', views.lista_ventas, name='lista'),
    path('crear/', views.crear_venta, name='crear'),
    path("editar-modal/<int:pk>/", views.editar_venta_modal, name="editar_modal"),
    path("<int:pk>/detalle-json/", views.detalle_venta_json, name="detalle_json"),
    path('anular/<int:venta_id>/', views.anular_venta, name='anular'),
    path("toggle-estado/<int:venta_id>/", views.toggle_estado_venta, name="toggle_estado"),
    path("reporte/vista-previa/", views.vista_previa_reporte_ventas, name="vista_previa_reporte"),
    path("reporte/exportar/", views.exportar_reporte_ventas, name="exportar_reporte"),
    # Devoluciones
    path("<int:venta_id>/devolucion/items/", views.devolucion_venta_json, name="devolucion_items"),
    path("<int:venta_id>/devolucion/registrar/", views.registrar_devolucion, name="registrar_devolucion"),
]
