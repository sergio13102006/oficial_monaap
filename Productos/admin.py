from django.contrib import admin
from .models import Marca, Producto


@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre', 'activo', 'fecha_creacion']
    list_filter = ['activo', 'fecha_creacion']
    search_fields = ['nombre', 'descripcion']
    list_editable = ['activo']
    ordering = ['nombre']

    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'descripcion', 'activo')
        }),
    )


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = [
        'codigo',
        'nombre',
        'marca',
        'precio',
        'precio_formateado',
        'linea',
        'presentacion',
        'unidad_medida',
        'fecha_creacion'
    ]

    list_filter = [
        'linea',
        'unidad_medida',
        'marca',
        'fecha_creacion'
    ]

    search_fields = [
        'codigo',
        'nombre',
        'descripcion',
        'linea',
        'marca',
    ]

    list_editable = [ 'precio']

    readonly_fields = ['codigo', 'fecha_creacion', 'fecha_actualizacion']

    ordering = ['-fecha_creacion']
    list_per_page = 25

    fieldsets = (
        ('Información Básica', {
            'fields': (
                'codigo',
                'nombre',
                'marca',
                'descripcion'
            )
        }),
        ('Detalles del Producto', {
            'fields': (
                'linea',
                'presentacion',
                'unidad_medida',
                'precio'
            )
        }),
        ('Estado y Fechas', {
            'fields': (
                'fecha_creacion',
                'fecha_actualizacion'
            )
        }),
    )

    def precio_formateado(self, obj):
        return obj.get_precio_formateado()

    precio_formateado.short_description = 'Precio'
    precio_formateado.admin_order_field = 'precio'

    actions = ['marcar_disponible', 'marcar_agotado', 'marcar_descontinuado']

    def marcar_disponible(self, request, queryset):
        count = queryset.update(estado='disponible')
        self.message_user(request, f'{count} producto(s) marcado(s) como disponible.')

    marcar_disponible.short_description = "Marcar como Disponible"

    def marcar_agotado(self, request, queryset):
        count = queryset.update(estado='agotado')
        self.message_user(request, f'{count} producto(s) marcado(s) como agotado.')

    marcar_agotado.short_description = "Marcar como Agotado"

    def marcar_descontinuado(self, request, queryset):
        count = queryset.update(estado='descontinuado')
        self.message_user(request, f'{count} producto(s) marcado(s) como descontinuado.')

    marcar_descontinuado.short_description = "Marcar como Descontinuado"