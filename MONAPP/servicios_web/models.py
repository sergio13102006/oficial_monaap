import re
import uuid

from django.core.exceptions import ValidationError
from django.db import models


_TEXTO_SEGURO_RE = re.compile(r'^[A-Za-z0-9ÁÉÍÓÚáéíóúÑñ\s]+$')


def _texto_seguro(valor: str) -> bool:
    return bool(_TEXTO_SEGURO_RE.match((valor or '').strip()))


class ServicioWeb(models.Model):
    id_servicio_web = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    servicio_origen = models.OneToOneField(
        'servicios.Servicio',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='servicio_web',
        verbose_name='Servicio origen'
    )

    nombre = models.CharField(max_length=200, verbose_name='Nombre del Servicio')
    descripcion = models.TextField(verbose_name='Descripción del Servicio')
    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Precio al público'
    )
    imagen = models.ImageField(
        upload_to='servicios_web/imagenes/',
        null=True,
        blank=True,
        verbose_name='Imagen del Servicio (opcional)'
    )
    video = models.FileField(
        upload_to='servicios_web/videos/',
        null=True,
        blank=True,
        verbose_name='Video del Servicio (opcional)'
    )
    activo = models.BooleanField(default=True, verbose_name='Activo')
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name='Última Modificación')

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Servicio Web'
        verbose_name_plural = 'Servicios Web'

    def __str__(self):
        return self.nombre

    def clean(self):
        super().clean()

        nombre = (self.nombre or '').strip()
        descripcion = (self.descripcion or '').strip()

        if not nombre:
            raise ValidationError({'nombre': 'El nombre es obligatorio.'})
        if len(nombre) < 3:
            raise ValidationError({'nombre': 'Debe tener al menos 3 caracteres.'})
        if not _texto_seguro(nombre):
            raise ValidationError({'nombre': 'Solo se permiten letras, números y espacios.'})

        qs = ServicioWeb.objects.filter(nombre__iexact=nombre)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError({'nombre': 'Ya existe un servicio web con ese nombre.'})

        if not descripcion:
            raise ValidationError({'descripcion': 'La descripción es obligatoria.'})
        if len(descripcion) < 10:
            raise ValidationError({'descripcion': 'Debe tener al menos 10 caracteres.'})
        if not _texto_seguro(descripcion):
            raise ValidationError({'descripcion': 'Solo se permiten letras, números y espacios.'})

        if self.precio is None or self.precio <= 0:
            raise ValidationError({'precio': 'El precio debe ser mayor a 0.'})

        if self.video:
            allowed_extensions = ('.mp4', '.webm', '.ogg', '.mov')
            nombre_video = self.video.name.lower()
            if not nombre_video.endswith(allowed_extensions):
                raise ValidationError({'video': 'Formato de video no permitido.'})
            max_size_mb = 25
            if self.video.size > max_size_mb * 1024 * 1024:
                raise ValidationError({'video': f'El video no puede superar {max_size_mb} MB.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
