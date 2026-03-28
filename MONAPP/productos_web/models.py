from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile


class ProductoWeb(models.Model):
    """
    Modelo exclusivo para el catálogo público de la web.
    Independiente del inventario interno.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(
        max_length=200,
        verbose_name='Nombre del Producto',
    )
    precio = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Precio Público',
        validators=[
            MinValueValidator(0.01, message='El precio debe ser mayor a $0.'),
            MaxValueValidator(9999999.99, message='El precio no puede superar $9,999,999.99.'),
        ],
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripción',
    )
    imagen = models.ImageField(
        upload_to='productos_web/',
        blank=True,
        null=True,
        verbose_name='Imagen',
    )
    visible = models.BooleanField(
        default=True,
        verbose_name='Visible en la Web',
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Creado')
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name='Modificado')

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Catálogo Web'
        verbose_name_plural = 'Catálogos Web'

    def clean(self):
        from django.core.exceptions import ValidationError

        errores = {}
        if self.nombre:
            nombre = self.nombre.strip()
            qs = ProductoWeb.objects.filter(nombre__iexact=nombre)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                errores['nombre'] = 'Ya existe un producto con este nombre.'
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
        return f"{self.nombre} – ${self.precio}"
