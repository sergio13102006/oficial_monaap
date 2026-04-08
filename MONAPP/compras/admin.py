from django.contrib import admin

from .models import Compra, DevolucionCompra


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ("id", "fecha", "proveedor", "cuenta_financiera", "precio_total", "anulada")
    list_filter = ("anulada", "fecha", "cuenta_financiera")
    search_fields = ("id", "proveedor__nombre_proveedor")


@admin.register(DevolucionCompra)
class DevolucionCompraAdmin(admin.ModelAdmin):
    list_display = ("id", "fecha", "compra", "proveedor", "total", "anulada")
    list_filter = ("anulada", "fecha")
    search_fields = ("id", "compra__id", "proveedor__nombre_proveedor")
