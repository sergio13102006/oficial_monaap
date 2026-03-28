from django.db import models
from django.core.exceptions import ValidationError


class Personal(models.Model):
    TIPOS_DOCUMENTO = [
        ("CC", "Cédula de Ciudadanía"),
        ("TI", "Tarjeta de Identidad"),
        ("PAS", "Pasaporte"),
        ("NIT", "NIT"),
    ]

    ROLES = [
        ("Administrador", "Administrador"),
        ("Auxiliar", "Auxiliar"),
        ("Colaborador", "Colaborador"),
    ]

    tipo_documento = models.CharField(max_length=5, choices=TIPOS_DOCUMENTO, default="CC")
    numero_documento = models.CharField(max_length=20, unique=True)

    nombres = models.CharField(max_length=150)
    apellidos = models.CharField(max_length=150)

    correo = models.EmailField()
    telefono = models.CharField(max_length=15)

    rol = models.CharField(max_length=20, choices=ROLES, default="Colaborador")

    activo = models.BooleanField(default=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

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

        if self.nombres:
            self.nombres = self.nombres.strip().title()
            if not self._sin_signos_peligrosos(self.nombres):
                errores["nombres"] = "Los nombres no pueden contener signos especiales."
            elif not self._solo_letras_y_espacios(self.nombres):
                errores["nombres"] = "Los nombres solo pueden contener letras y espacios."

        if self.apellidos:
            self.apellidos = self.apellidos.strip().title()
            if not self._sin_signos_peligrosos(self.apellidos):
                errores["apellidos"] = "Los apellidos no pueden contener signos especiales."
            elif not self._solo_letras_y_espacios(self.apellidos):
                errores["apellidos"] = "Los apellidos solo pueden contener letras y espacios."

        if self.telefono:
            self.telefono = self.telefono.strip()
            if not self._sin_signos_peligrosos(self.telefono):
                errores["telefono"] = "El telefono no puede contener signos especiales."
            elif not self._solo_numeros(self.telefono):
                errores["telefono"] = "El telefono solo puede contener numeros."

        if self.correo:
            self.correo = self.correo.strip()
            if not self._sin_signos_peligrosos(self.correo):
                errores["correo"] = "El correo no puede contener signos especiales."

        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombres} {self.apellidos} - {self.numero_documento}"
