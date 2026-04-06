import os

from django.conf import settings
from django.db import models

from .constants import (
    BACKUP_ACTION_CREATED,
    BACKUP_ACTION_FAILED,
    BACKUP_ACTION_IMPORTED,
    BACKUP_ACTION_RESTORED,
    BACKUP_ACTION_SECURITY,
    BACKUP_DEFAULT_RESTORE_MODE,
    DB_ENGINE_POSTGRES,
    DB_ENGINE_SQLITE,
    RESTORE_MODE_MIRROR,
    RESTORE_MODE_OVERWRITE,
)


class BackupRecord(models.Model):
    """Registro de cada backup realizado."""

    ACCION_CHOICES = [
        (BACKUP_ACTION_CREATED, 'Creado'),
        (BACKUP_ACTION_IMPORTED, 'Importado'),
        (BACKUP_ACTION_RESTORED, 'Restaurado'),
        (BACKUP_ACTION_SECURITY, 'Backup previo a restaurar'),
        (BACKUP_ACTION_FAILED, 'Fallido'),
        ('fallido_creacion', 'Fallo al crear'),
        ('fallido_restauracion', 'Fallo al restaurar'),
        ('fallido_importacion', 'Fallo al importar'),
    ]

    DB_ENGINE_CHOICES = [
        (DB_ENGINE_SQLITE, 'SQLite'),
        (DB_ENGINE_POSTGRES, 'PostgreSQL'),
    ]

    TIPO_CHOICES = [
        ('completo', 'Completo (BD + Media)'),
        ('base_datos', 'Solo Base de Datos'),
        ('media', 'Solo Archivos Media'),
    ]

    ESTADO_CHOICES = [
        ('exitoso', 'Exitoso'),
        ('fallido', 'Fallido'),
        ('en_progreso', 'En Progreso'),
        ('restaurado', 'Restaurado'),
    ]

    nombre = models.CharField(max_length=255, verbose_name="Nombre del backup")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='completo')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='en_progreso')
    archivo = models.CharField(max_length=500, blank=True, null=True, verbose_name="Ruta del archivo")
    tamano = models.BigIntegerField(default=0, verbose_name="Tamaño en bytes")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='backups_creados',
    )
    notas = models.TextField(blank=True, default='', verbose_name="Notas / Observaciones")
    es_automatico = models.BooleanField(default=False, verbose_name="¿Backup automático?")
    tablas_incluidas = models.TextField(
        blank=True, default='',
        verbose_name="Tablas incluidas",
        help_text="Lista de tablas incluidas en el backup (separadas por coma)."
    )
    duracion_segundos = models.FloatField(default=0, verbose_name="Duración (seg)")

    ultima_accion = models.CharField(max_length=20, choices=ACCION_CHOICES, default='creado', verbose_name="Ultima accion")
    veces_restaurado = models.PositiveIntegerField(default=0, verbose_name="Veces restaurado")
    fecha_ultima_restauracion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha ultima restauracion")

    checksum = models.CharField(max_length=128, blank=True, default='', verbose_name="Checksum")
    db_engine = models.CharField(max_length=30, choices=DB_ENGINE_CHOICES, default=DB_ENGINE_SQLITE, verbose_name="Motor de base de datos")
    incluye_media = models.BooleanField(default=False, verbose_name="Incluye media")
    origen = models.CharField(max_length=120, blank=True, default='local', verbose_name="Origen")
    es_backup_seguridad = models.BooleanField(default=False, verbose_name="Es backup de seguridad")
    backup_padre = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='backups_derivados')
    detalle_error = models.TextField(blank=True, default='', verbose_name="Detalle de error")

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = "Backup"
        verbose_name_plural = "Backups"

    def __str__(self):
        return f"{self.nombre} - {self.get_tipo_display()} ({self.fecha_creacion:%Y-%m-%d %H:%M})"

    @property
    def tamano_legible(self):
        """Devuelve el tamaño en formato legible (KB, MB, GB)."""
        size = self.tamano
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    @property
    def archivo_existe(self):
        if self.archivo:
            return os.path.exists(self.archivo)
        return False

    @property
    def veces_usado(self):
        return self.veces_restaurado

    @property
    def nombre_visible(self):
        return self.nombre

    @property
    def tipo_backup(self):
        return self.tipo

    @property
    def accion(self):
        return self.ultima_accion

    @property
    def archivo_zip(self):
        return self.archivo

    @property
    def tamano_bytes(self):
        return self.tamano

    @property
    def creado_en(self):
        return self.fecha_creacion

    @property
    def restaurado_en(self):
        return self.fecha_ultima_restauracion


class BackupConfig(models.Model):
    """Configuración global de backups."""

    backup_automatico = models.BooleanField(default=False, verbose_name="Backup automático activo")
    frecuencia_horas = models.PositiveIntegerField(default=24, verbose_name="Frecuencia (horas)")
    max_backups = models.PositiveIntegerField(default=10, verbose_name="Máximo de backups a conservar")
    incluir_media = models.BooleanField(default=True, verbose_name="Incluir archivos media")
    restore_mode_default = models.CharField(max_length=20, choices=[(RESTORE_MODE_OVERWRITE, "Overwrite"), (RESTORE_MODE_MIRROR, "Mirror")], default=BACKUP_DEFAULT_RESTORE_MODE, verbose_name="Modo restore por defecto")
    crear_backup_pre_restore = models.BooleanField(default=True, verbose_name="Crear backup antes de restaurar")
    permitir_restore_cross_engine = models.BooleanField(
        default=False,
        verbose_name="Habilitar migracion asistida entre motores",
        help_text="No habilita restauracion operativa directa entre motores distintos; solo reserva el modulo para flujos de migracion/importacion controlados.",
    )
    habilitar_mirror_media = models.BooleanField(default=False, verbose_name="Habilitar mirror de media")
    retencion_backups_seguridad = models.PositiveIntegerField(default=3, verbose_name="Retencion backups de seguridad")
    ruta_backups = models.CharField(
        max_length=500, blank=True, default='',
        verbose_name="Ruta personalizada",
        help_text="Dejar vacío para usar la ruta por defecto (backups/)"
    )
    ultimo_backup = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Configuración de Backup"
        verbose_name_plural = "Configuración de Backups"

    def __str__(self):
        return "Configuración de Backups"

    def save(self, *args, **kwargs):
        # Singleton: solo permitir una instancia
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_config(cls):
        config, _ = cls.objects.get_or_create(pk=1)
        return config
