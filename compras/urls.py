from django.urls import path
from . import views

app_name = "compras"

urlpatterns = [
    path("", views.lista_compras, name="lista_compras"),
    path("crear/", views.crear_compra, name="crear_compra"),
    path("editar/<int:pk>/", views.editar_compra, name="editar_compra"),
    path("detalle/<int:compra_id>/", views.detalle_compra, name="detalle_compra"),
    path("anular/<int:pk>/", views.anular_compra, name="anular_compra"),
    
    path("comprobante/<int:pk>/preview/", views.comprobante_compra_preview, name="comprobante_vista_previa"),
    path("comprobante/<int:pk>/excel/", views.comprobante_compra_excel, name="comprobante_compra_excel"),
    
    path("devolucion/crear/", views.crear_devolucion_compra, name="crear_devolucion_compra"),
    path("ajax/cargar-detalles-compra/", views.cargar_detalles_compra, name="cargar_detalles_compra"),
    path("devoluciones/anular/<int:pk>/", views.anular_devolucion_compra, name="anular_devolucion_compra"),
    path("devoluciones/comprobante/<int:pk>/preview/", views.comprobante_devolucion_compra_preview,name="comprobante_devolucion_compra_preview"),    
]