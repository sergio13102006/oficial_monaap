from django.db import models
from django.core.exceptions import ValidationError
from django.utils.timezone import now


class Cliente(models.Model):
    TIPO_DOCUMENTO_CHOICES = [
        ("CC", "Cedula de ciudadanía"),
        ("TI", "Tarjeta de identidad"),
        ("CE", "Cedula de extranjería"),
        ("PP", "Pasaporte"),
    ]

    ESTADO_CHOICES = [
        ("activo", "Activo"),
        ("inactivo", "Inactivo"),
    ]

    codigo_cliente = models.CharField(max_length=10, unique=True, editable=False)
    tipo_documento = models.CharField(max_length=2, choices=TIPO_DOCUMENTO_CHOICES)
    numero_documento = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField()
    telefono = models.CharField(max_length=20, blank=True, null=True)
    correo = models.EmailField(blank=True, null=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default="activo")
    fecha_registro = models.DateTimeField(default=now)

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

        if self.numero_documento:
            self.numero_documento = self.numero_documento.strip()
            if not self._sin_signos_peligrosos(self.numero_documento):
                errores["numero_documento"] = "El numero de documento no puede contener signos especiales."
            elif not self._solo_numeros(self.numero_documento):
                errores["numero_documento"] = "El numero de documento solo puede contener numeros."

        if self.nombre:
            self.nombre = self.nombre.strip().title()
            if not self._sin_signos_peligrosos(self.nombre):
                errores["nombre"] = "El nombre no puede contener signos especiales."
            elif not self._solo_letras_y_espacios(self.nombre):
                errores["nombre"] = "El nombre solo puede contener letras y espacios."

        if self.apellido:
            self.apellido = self.apellido.strip().title()
            if not self._sin_signos_peligrosos(self.apellido):
                errores["apellido"] = "El apellido no puede contener signos especiales."
            elif not self._solo_letras_y_espacios(self.apellido):
                errores["apellido"] = "El apellido solo puede contener letras y espacios."

        if self.telefono:
            self.telefono = self.telefono.strip()
            if not self._sin_signos_peligrosos(self.telefono):
                errores["telefono"] = "El telefono no puede contener signos especiales."
            elif not self._solo_numeros(self.telefono):
                errores["telefono"] = "El telefono solo puede contener numeros."

        if self.correo:
            self.correo = self.correo.strip()
            if not self._sin_signos_peligrosos(self.correo):
                errores["correo"] = "El correo no puede contener signos HTML."

        if self.fecha_nacimiento:
            from datetime import date
            if self.fecha_nacimiento > date.today():
                errores["fecha_nacimiento"] = "La fecha no puede ser futura."

        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        if not self.codigo_cliente:
            ultimo = Cliente.objects.all().order_by("-id").first()
            if ultimo:
                numero = int(ultimo.codigo_cliente.replace("CL", "")) + 1
            else:
                numero = 1
            self.codigo_cliente = f"CL{numero:04d}"

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} {self.apellido}"
