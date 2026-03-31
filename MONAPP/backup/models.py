import os
from django.db import models
from django.conf import settings


class BackupRecord(models.Model):
    """Registro de cada backup realizado."""

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


class BackupConfig(models.Model):
    """Configuración global de backups."""

    backup_automatico = models.BooleanField(default=False, verbose_name="Backup automático activo")
    frecuencia_horas = models.PositiveIntegerField(default=24, verbose_name="Frecuencia (horas)")
    max_backups = models.PositiveIntegerField(default=10, verbose_name="Máximo de backups a conservar")
    incluir_media = models.BooleanField(default=True, verbose_name="Incluir archivos media")
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
