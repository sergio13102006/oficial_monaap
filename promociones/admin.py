from django.contrib import admin
from .models import Promocion


@admin.register(Promocion)
class PromocionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'etiqueta', 'porcentaje_descuento', 'fecha_inicio', 'fecha_fin', 'activa', 'fecha_creacion')
    list_filter = ('activa', 'etiqueta')
    search_fields = ('nombre',)
