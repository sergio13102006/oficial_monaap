from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
import uuid


class Servicio(models.Model):
    id_servicio = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    nombre = models.CharField(
        max_length=200,
        verbose_name="Nombre del Servicio"
    )
    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Precio",
    )
    descripcion = models.TextField(
        verbose_name="Descripción"
    )
    imagen = models.ImageField(
        upload_to="servicios/",
        null=True,
        blank=True,
        verbose_name="Imagen del Servicio",
    )
    video = models.FileField(
        upload_to="servicios/videos/",
        null=True,
        blank=True,
        verbose_name="Video del Servicio",
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="Activo"
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Creación"
    )
    fecha_modificacion = models.DateTimeField(
        auto_now=True,
        verbose_name="Última Modificación"
    )

    class Meta:
        ordering = ["-fecha_creacion"]
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"

    @staticmethod
    def _solo_letras_numeros_y_espacios(valor):
        valor = (valor or "").strip()
        return bool(valor) and all(ch.isalnum() or ch.isspace() for ch in valor)

    @staticmethod
    def _texto_seguro(valor):
        valor = (valor or "").strip()
        return "<" not in valor and ">" not in valor

    def _nombre_duplicado(self):
        qs = Servicio.objects.filter(nombre__iexact=(self.nombre or "").strip())
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        return qs.exists()

    def clean(self):
        errores = {}

        if self.nombre:
            self.nombre = " ".join(self.nombre.strip().split())

            if not self._texto_seguro(self.nombre):
                errores["nombre"] = "El nombre no puede contener los signos < o >."
            elif not self._solo_letras_numeros_y_espacios(self.nombre):
                errores["nombre"] = "El nombre solo puede contener letras, números y espacios."
            elif self._nombre_duplicado():
                errores["nombre"] = "Ya existe un servicio con este nombre."
        else:
            errores["nombre"] = "El nombre del servicio es obligatorio."

        if self.descripcion:
            self.descripcion = self.descripcion.strip()

            if not self._texto_seguro(self.descripcion):
                errores["descripcion"] = "La descripción no puede contener los signos < o >."
            elif len(self.descripcion) < 10:
                errores["descripcion"] = "La descripción debe tener al menos 10 caracteres."
        else:
            errores["descripcion"] = "La descripción es obligatoria."

        if self.precio is None:
            errores["precio"] = "El precio es obligatorio."
        elif self.precio < 0:
            errores["precio"] = "El precio no puede ser negativo."

        if self.imagen:
            content_type = getattr(self.imagen, "content_type", "")
            if content_type and not content_type.startswith("image/"):
                errores["imagen"] = "Debes subir un archivo de imagen válido."

        if self.video:
            content_type = getattr(self.video, "content_type", "")
            if content_type and not content_type.startswith("video/"):
                errores["video"] = "Debes subir un archivo de video válido."

        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} - ${self.precio}"
