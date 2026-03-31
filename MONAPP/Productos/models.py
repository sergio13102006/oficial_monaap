from django.db import models
from django.core.exceptions import ValidationError
import re


class Marca(models.Model):
    """
    Modelo para las marcas de productos
    """

    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Marca"
        verbose_name_plural = "Marcas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    UNIDAD_MEDIDA_CHOICES = (
        ("unidad", "Unidad"),
        ("kg", "Kilogramo"),
        ("g", "Gramo"),
        ("litro", "Litro"),
        ("ml", "Mililitro"),
        ("caja", "Caja"),
        ("paquete", "Paquete"),
        ("metro", "Metro"),
    )

    codigo = models.AutoField(primary_key=True)
    marca = models.CharField(max_length=100)
    nombre = models.CharField(
        max_length=60,
        verbose_name="Nombre del Producto",
        help_text="Nombre del producto",
        unique=True,
    )

    precio = models.IntegerField(
        verbose_name="Precio",
        help_text="Precio del producto en pesos colombianos",
    )

    descripcion = models.TextField(blank=True, verbose_name="Descripcion")

    linea = models.CharField(max_length=45, blank=True, verbose_name="Linea")

    presentacion = models.CharField(max_length=50, blank=True, verbose_name="Presentacion")

    unidad_medida = models.CharField(
        max_length=45,
        choices=UNIDAD_MEDIDA_CHOICES,
        verbose_name="Unidad de Medida",
    )

    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    imagen = models.ImageField(upload_to="productos/", blank=True, null=True)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ["nombre"]
        indexes = [
            models.Index(fields=["nombre"]),
            models.Index(fields=["linea"]),
        ]

    @staticmethod
    def _solo_letras_y_espacios(valor):
        valor = (valor or "").strip()
        return bool(valor) and all(ch.isalpha() or ch.isspace() for ch in valor)

    @staticmethod
    def _solo_letras_numeros_y_espacios(valor):
        valor = (valor or "").strip()
        return bool(valor) and all(ch.isalnum() or ch.isspace() for ch in valor)

    @staticmethod
    def _solo_numeros(valor):
        valor = (valor or "").strip()
        return bool(valor) and valor.isdigit()

    @staticmethod
    def _sin_signos_peligrosos(valor):
        valor = (valor or "").strip()
        return "<" not in valor and ">" not in valor

    def clean(self):
        errores = {}

        if self.marca:
            self.marca = self.marca.strip().title()
            if not self._sin_signos_peligrosos(self.marca):
                errores["marca"] = "La marca no puede contener signos especiales."
            elif not self._solo_letras_y_espacios(self.marca):
                errores["marca"] = "La marca solo puede contener letras y espacios."

        if self.nombre:
            self.nombre = self.nombre.strip().title()
            if not self._sin_signos_peligrosos(self.nombre):
                errores["nombre"] = "El nombre no puede contener signos especiales."
            elif not self._solo_letras_numeros_y_espacios(self.nombre):
                errores["nombre"] = "El nombre solo puede contener letras, numeros y espacios."
            elif not any(ch.isalpha() for ch in self.nombre):
                errores["nombre"] = "El nombre debe contener al menos una letra."

        if self.precio is not None:
            precio_str = str(self.precio).strip()
            if not precio_str:
                errores["precio"] = "El precio es obligatorio."
            elif re.search(r"[^\d\s\.,]", precio_str):
                errores["precio"] = "El precio solo puede contener numeros."
            else:
                normalizado = precio_str.replace(".", "").replace(",", "").replace(" ", "")
                if not normalizado.isdigit():
                    errores["precio"] = "El precio solo puede contener numeros."
                else:
                    self.precio = int(normalizado)

        if self.descripcion:
            self.descripcion = self.descripcion.strip()
            if not self._sin_signos_peligrosos(self.descripcion):
                errores["descripcion"] = "La descripcion no puede contener signos de HTML."

        if self.linea:
            self.linea = self.linea.strip().title()
            if not self._sin_signos_peligrosos(self.linea):
                errores["linea"] = "La linea no puede contener signos especiales."
            elif not self._solo_letras_y_espacios(self.linea):
                errores["linea"] = "La linea solo puede contener letras y espacios."

        if self.presentacion:
            self.presentacion = self.presentacion.strip()
            if not self._sin_signos_peligrosos(self.presentacion):
                errores["presentacion"] = "La presentacion no puede contener signos especiales."
            elif not self._solo_numeros(self.presentacion):
                errores["presentacion"] = "La presentacion solo debe contener numeros."

        if self.nombre and Producto.objects.exclude(pk=self.pk).filter(nombre__iexact=self.nombre).exists():
            errores["nombre"] = "Ya existe un producto con este nombre."

        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        if isinstance(self.precio, str):
            normalizado = re.sub(r"[^\d]", "", self.precio)
            if normalizado:
                self.precio = int(normalizado)
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    def get_precio_formateado(self):
        return f"${self.precio:,}".replace(",", ".")

    def esta_disponible(self):
        return self.activo

    def get_nombre_completo(self):
        if self.presentacion:
            return f"{self.nombre} - {self.presentacion}"
        return self.nombre

    @property
    def stock_actual(self):
        stock_obj = getattr(self, "stock", None)
        return stock_obj.cantidad_actual if stock_obj else 0

    @property
    def imagen_crud(self):
        if self.imagen:
            return self.imagen.url
        return ""
