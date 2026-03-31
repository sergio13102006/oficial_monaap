from django import forms
from django.core.exceptions import ValidationError
from core.form_validations import ValidationFormMixin
from .models import Personal


def _solo_letras_y_espacios(valor):
    valor = (valor or "").strip()
    return bool(valor) and all(ch.isalpha() or ch.isspace() for ch in valor)


def _solo_numeros(valor):
    valor = (valor or "").strip()
    return bool(valor) and valor.isdigit()


def _sin_signos_peligrosos(valor):
    valor = (valor or "").strip()
    return "<" not in valor and ">" not in valor


class PersonalForm(ValidationFormMixin, forms.ModelForm):
    class Meta:
        model = Personal
        fields = ["tipo_documento", "numero_documento", "nombres", "apellidos", "telefono", "correo", "rol", "activo"]
        widgets = {
            "tipo_documento": forms.Select(
                attrs={
                    "class": "personal-form-control",
                }
            ),
            "numero_documento": forms.TextInput(
                attrs={
                    "class": "personal-form-control",
                    "placeholder": "Ingrese numero de documento",
                    "pattern": "[0-9]+",
                    "title": "Solo se permiten numeros",
                    "maxlength": "12",
                    "data-validate": "numeric",
                }
            ),
            "nombres": forms.TextInput(
                attrs={
                    "class": "personal-form-control",
                    "placeholder": "Ingrese nombres",
                    "title": "Solo se permiten letras y espacios",
                    "data-validate": "alpha",
                }
            ),
            "apellidos": forms.TextInput(
                attrs={
                    "class": "personal-form-control",
                    "placeholder": "Ingrese apellidos",
                    "title": "Solo se permiten letras y espacios",
                    "data-validate": "alpha",
                }
            ),
            "telefono": forms.TextInput(
                attrs={
                    "class": "personal-form-control",
                    "placeholder": "Ingrese telefono",
                    "pattern": "[0-9]+",
                    "title": "Solo se permiten numeros",
                    "maxlength": "10",
                    "data-validate": "numeric",
                }
            ),
            "correo": forms.EmailInput(
                attrs={
                    "class": "personal-form-control",
                    "placeholder": "Ingrese correo electronico",
                    "data-validate": "text",
                }
            ),
            "rol": forms.Select(
                attrs={
                    "class": "personal-form-control",
                }
            ),
            "activo": forms.CheckboxInput(
                attrs={
                    "class": "personal-switch-input",
                }
            ),
        }

    def clean_numero_documento(self):
        numero_documento = (self.cleaned_data.get("numero_documento") or "").strip()
        if not _sin_signos_peligrosos(numero_documento):
            raise ValidationError("El numero de documento no puede contener signos especiales.")
        if not _solo_numeros(numero_documento):
            raise ValidationError("El numero de documento solo puede contener numeros.")
        return numero_documento

    def clean_nombres(self):
        nombres = (self.cleaned_data.get("nombres") or "").strip()
        if not nombres:
            raise ValidationError("Los nombres son obligatorios.")
        if not _sin_signos_peligrosos(nombres):
            raise ValidationError("Los nombres no pueden contener signos especiales.")
        if not _solo_letras_y_espacios(nombres):
            raise ValidationError("Los nombres solo pueden contener letras y espacios.")
        return nombres.title()

    def clean_apellidos(self):
        apellidos = (self.cleaned_data.get("apellidos") or "").strip()
        if not apellidos:
            raise ValidationError("Los apellidos son obligatorios.")
        if not _sin_signos_peligrosos(apellidos):
            raise ValidationError("Los apellidos no pueden contener signos especiales.")
        if not _solo_letras_y_espacios(apellidos):
            raise ValidationError("Los apellidos solo pueden contener letras y espacios.")
        return apellidos.title()

    def clean_telefono(self):
        telefono = (self.cleaned_data.get("telefono") or "").strip()
        if not telefono:
            raise ValidationError("El telefono es obligatorio.")
        if not _sin_signos_peligrosos(telefono):
            raise ValidationError("El telefono no puede contener signos especiales.")
        if not _solo_numeros(telefono):
            raise ValidationError("El telefono solo puede contener numeros.")
        return telefono

    def clean_correo(self):
        correo = (self.cleaned_data.get("correo") or "").strip()
        if not correo:
            raise ValidationError("El correo electronico es obligatorio.")
        if not _sin_signos_peligrosos(correo):
            raise ValidationError("El correo no puede contener signos especiales.")
        return correo


class PersonalBusquedaForm(ValidationFormMixin, forms.Form):
    busqueda = forms.CharField(
        required=False,
        label="Buscar por ID, documento, nombres o contacto",
        widget=forms.TextInput(
            attrs={
                "class": "personal-form-control",
                "placeholder": "Ingrese termino de busqueda",
            }
        ),
    )
    filtro = forms.ChoiceField(
        required=False,
        label="Filtrar por",
        choices=[
            ("activo", "Activos"),
            ("inactivo", "Inactivos"),
            ("todos", "Todos"),
        ]
        + [("rol_" + rol[0], rol[1]) for rol in Personal.ROLES],
        initial="todos",
        widget=forms.Select(
            attrs={
                "class": "personal-form-control",
                "id": "id_filtro_personal",
                "onchange": "enviarFormularioFiltro(this.form)",
            }
        ),
    )
