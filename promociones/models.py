from django.db import models
import uuid
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile


class Promocion(models.Model):
    """Modelo para gestionar promociones con descuento y vigencia."""

    ETIQUETA_CHOICES = [
        ('nuevo', 'Nuevo'),
        ('especial', 'Especial'),
        ('limitado', 'Limitado'),
        ('descuento', 'Descuento'),
        ('exclusivo', 'Exclusivo'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(
        max_length=200,
        verbose_name='Nombre de la Promoción',
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripción',
        help_text='Texto que se muestra en la tarjeta pública',
    )
    etiqueta = models.CharField(
        max_length=20,
        choices=ETIQUETA_CHOICES,
        default='nuevo',
        verbose_name='Etiqueta',
        help_text='Badge visible en la web pública',
    )
    porcentaje_descuento = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name='% de Descuento',
        help_text='Valor entre 0 y 100',
    )
    fecha_inicio = models.DateField(
        verbose_name='Fecha de Inicio',
    )
    fecha_fin = models.DateField(
        verbose_name='Fecha de Fin',
    )
    imagen = models.ImageField(
        upload_to='promociones/',
        blank=True,
        null=True,
        verbose_name='Imagen',
    )
    activa = models.BooleanField(
        default=True,
        verbose_name='Activa',
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Creado')
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name='Modificado')

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Promoción'
        verbose_name_plural = 'Promociones'

    def clean(self):
        from django.core.exceptions import ValidationError

        errores = {}
        if self.nombre:
            nombre = self.nombre.strip()
            qs = Promocion.objects.filter(nombre__iexact=nombre)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                errores['nombre'] = 'Ya existe una promocion con este nombre.'
        if errores:
            raise ValidationError(errores)

    def resize_image(self):
        """Redimensiona la imagen a un tamaño máximo de 400x300px manteniendo la proporción"""
        if self.imagen:
            try:
                img = Image.open(self.imagen)
                
                # Convertir a RGB si es necesario (para PNGs con transparencia)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                
                # Redimensionar manteniendo proporción (máximo 400x300)
                max_size = (400, 300)
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Guardar en memoria
                output = BytesIO()
                img.save(output, format='JPEG', quality=85, optimize=True)
                output.seek(0)
                
                # Reemplazar el archivo original con el redimensionado
                filename = self.imagen.name.split('.')[0] + '.jpg'
                self.imagen.save(
                    filename,
                    ContentFile(output.read()),
                    save=False
                )
            except Exception:
                # Si hay error, mantener imagen original
                pass

    def save(self, *args, **kwargs):
        # Si hay una imagen nueva, redimensionarla
        if self.imagen:
            self.resize_image()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} – {self.porcentaje_descuento}%"
