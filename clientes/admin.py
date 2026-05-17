from django.contrib import admin
from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = (
        'codigo_cliente',
        'nombre',
        'apellido',
        'tipo_documento',
        'numero_documento',
        'estado',
    )
    search_fields = (
        'codigo_cliente',
        'nombre',
        'apellido',
        'numero_documento',
    )
    list_filter = ('estado',)
