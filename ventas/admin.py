from django.contrib import admin
from .models import Venta


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = (
        'codigo_venta',
        'cliente',
        'fecha',
        'estado',
        'total',
    )

    search_fields = (
        'codigo_venta',
        'cliente__nombre',
        'cliente__apellido',
        'codigo_producto',
        'nombre_colaborador',
    )

    list_filter = ('fecha',)
