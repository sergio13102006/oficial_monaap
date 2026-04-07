from django.contrib import admin
from .models import AtencionServicio, GestionAlisado, TratamientoDatosFirmado


@admin.register(GestionAlisado)
class GestionAlisadoAdmin(admin.ModelAdmin):
    list_display = ['fecha_hora', 'procedimiento_realizado_por', 'tipo_alisado', 'precio_alisado', 'saldo_pendiente']
    list_filter = ['fecha_hora', 'tipo_alisado', 'es_oferta_especial', 'medio_pago']
    search_fields = ['procedimiento_realizado_por', 'recomendaciones_post_cuidados']
    readonly_fields = ['id_gestion', 'fecha_hora']
    ordering = ['-fecha_hora']
    date_hierarchy = 'fecha_hora'
    
    fieldsets = (
        ('Información del Servicio y Pago', {
            'fields': ('precio_alisado', 'es_oferta_especial', 'descripcion_oferta', 
                      'anticipo_cliente', 'medio_pago', 'saldo_pendiente')
        }),
        ('Información del Procedimiento', {
            'fields': ('procedimiento_realizado_por', 'fecha_hora', 'tipo_alisado', 
                      'requiere_resellado', 'porcentaje_alisado', 'despunte_hoy')
        }),
        ('Características del Cabello', {
            'fields': ('porosidad', 'textura', 'forma_natural', 'elasticidad', 
                      'longitud', 'densidad', 'piel_cabelludo', 'alopecia', 
                      'caida_cabello', 'caspa'),
            'classes': ('collapse',)
        }),
        ('Estado de Salud', {
            'fields': ('lactante', 'gestante', 'sufre_tiroides', 'medicamento_tiroides'),
            'classes': ('collapse',)
        }),
        ('Procesos Químicos', {
            'fields': ('procesos_tintura', 'procesos_decoloracion', 'procesos_ondulados',
                      'procesos_extracciones', 'procesos_alisados', 'procesos_super_aclarante',
                      'procesos_otro'),
            'classes': ('collapse',)
        }),
        ('Hábitos y Cuidados', {
            'fields': ('cuenta_con_secador', 'frecuencia_recoge_cabello', 'realiza_ejercicio',
                      'frecuencia_ejercicio', 'usa_casco', 'productos_capilares',
                      'se_bana_agua_caliente', 'requiere_refuerzo_15dias'),
            'classes': ('collapse',)
        }),
        ('Recomendaciones', {
            'fields': ('recomendaciones_post_cuidados',)
        }),
        ('Metadatos', {
            'fields': ('id_gestion',),
            'classes': ('collapse',)
        }),
    )


@admin.register(AtencionServicio)
class AtencionServicioAdmin(admin.ModelAdmin):
    list_display = ['fecha_atencion', 'cliente', 'tipo_servicio', 'profesional_o_asesor', 'estado_atencion', 'tratamiento_completado']
    list_filter = ['estado_atencion', 'tipo_servicio', 'sede', 'fecha_atencion']
    search_fields = ['cliente__nombre', 'cliente__apellido', 'cliente__numero_documento', 'profesional_o_asesor', 'tipo_servicio']
    readonly_fields = ['id_atencion', 'creado_en', 'actualizado_en']


@admin.register(TratamientoDatosFirmado)
class TratamientoDatosFirmadoAdmin(admin.ModelAdmin):
    list_display = ['creado_en', 'cliente', 'atencion', 'estado', 'version_tratamiento', 'tablet_utilizada']
    list_filter = ['estado', 'version_tratamiento', 'sede', 'creado_en']
    search_fields = ['cliente__nombre', 'cliente__apellido', 'cliente__numero_documento', 'hash_integridad']
    readonly_fields = ['id_tratamiento', 'hash_integridad', 'creado_en', 'actualizado_en', 'fecha_hora_firma']
