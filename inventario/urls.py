from django.urls import path
from . import views

app_name = 'inventario'
urlpatterns = [
    path('', views.inventario_lista, name='inventario_lista'),
    path('reporte-stock.csv', views.reporte_stock_csv, name='reporte_stock_csv'),
]
