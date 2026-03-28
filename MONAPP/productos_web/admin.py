from django.contrib import admin
from .models import ProductoWeb


@admin.register(ProductoWeb)
class ProductoWebAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio', 'visible', 'fecha_creacion')
    list_filter = ('visible',)
    search_fields = ('nombre',)
