from django.db import models
from django.core.exceptions import ValidationError


class Proveedor(models.Model):
    ESTADO_CHOICES = [
        ("activo", "Activo"),
        ("inactivo", "Inactivo"),
    ]

    nit = models.CharField(max_length=20, unique=True, verbose_name="NIT")
    nombre_proveedor = models.CharField(max_length=150, unique=True, verbose_name="Proveedor")
    telefono_proveedor = models.CharField(max_length=20, verbose_name="Teléfono")
    correo_proveedor = models.EmailField(verbose_name="Correo")
    direccion_proveedor = models.CharField(max_length=200, verbose_name="Dirección")
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default="activo")

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ["nombre_proveedor"]
        indexes = [
            models.Index(fields=["nombre_proveedor"]),
            models.Index(fields=["nit"]),
            models.Index(fields=["estado"]),
        ]

    @staticmethod
    def _solo_letras_y_espacios(valor):
        valor = (valor or "").strip()
        return bool(valor) and all(ch.isalpha() or ch.isspace() for ch in valor)

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

        if self.nit:
            self.nit = self.nit.strip()
            if not self._sin_signos_peligrosos(self.nit):
                errores["nit"] = "El NIT no puede contener signos especiales."
            elif not self._solo_numeros(self.nit):
                errores["nit"] = "El NIT solo debe contener numeros."
            elif len(self.nit) < 7 or len(self.nit) > 15:
                errores["nit"] = "El NIT debe tener entre 7 y 15 digitos."

        if self.nombre_proveedor:
            self.nombre_proveedor = self.nombre_proveedor.strip().title()
            if not self._sin_signos_peligrosos(self.nombre_proveedor):
                errores["nombre_proveedor"] = "El nombre no puede contener signos especiales."
            elif not self._solo_letras_y_espacios(self.nombre_proveedor):
                errores["nombre_proveedor"] = "El nombre del proveedor solo debe contener letras y espacios."

        if self.telefono_proveedor:
            self.telefono_proveedor = self.telefono_proveedor.strip()
            if not self._sin_signos_peligrosos(self.telefono_proveedor):
                errores["telefono_proveedor"] = "El telefono no puede contener signos especiales."
            elif not self._solo_numeros(self.telefono_proveedor):
                errores["telefono_proveedor"] = "El telefono solo debe contener numeros."
            elif len(self.telefono_proveedor) != 10:
                errores["telefono_proveedor"] = "El telefono debe tener exactamente 10 digitos."

        if self.direccion_proveedor:
            self.direccion_proveedor = self.direccion_proveedor.strip().title()
            if not self._sin_signos_peligrosos(self.direccion_proveedor):
                errores["direccion_proveedor"] = "La direccion no puede contener signos HTML."
            elif any(not (ch.isalnum() or ch.isspace()) for ch in self.direccion_proveedor):
                errores["direccion_proveedor"] = "La direccion solo puede contener letras, numeros y espacios."

        if self.nit and Proveedor.objects.exclude(pk=self.pk).filter(nit__iexact=self.nit).exists():
            errores["nit"] = "Ya existe un proveedor con este NIT."

        if self.nombre_proveedor and Proveedor.objects.exclude(pk=self.pk).filter(
            nombre_proveedor__iexact=self.nombre_proveedor
        ).exists():
            errores["nombre_proveedor"] = "Ya existe un proveedor con este nombre."

        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre_proveedor} ({self.nit})"
