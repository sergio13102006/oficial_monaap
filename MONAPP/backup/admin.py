from django.contrib import admin
from .models import BackupRecord, BackupConfig


@admin.register(BackupRecord)
class BackupRecordAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'estado', 'tamano_legible', 'fecha_creacion', 'usuario')
    list_filter = ('tipo', 'estado', 'es_automatico')
    search_fields = ('nombre', 'notas')
    readonly_fields = ('fecha_creacion',)


@admin.register(BackupConfig)
class BackupConfigAdmin(admin.ModelAdmin):
    list_display = ('backup_automatico', 'frecuencia_horas', 'max_backups', 'ultimo_backup')
