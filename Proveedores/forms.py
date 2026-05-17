from django import forms
from core.form_validations import ValidationFormMixin
from .models import Proveedor


def _solo_letras_y_espacios(valor):
    valor = (valor or "").strip()
    return bool(valor) and all(ch.isalpha() or ch.isspace() for ch in valor)


def _solo_numeros(valor):
    valor = (valor or "").strip()
    return bool(valor) and valor.isdigit()


def _sin_signos_peligrosos(valor):
    valor = (valor or "").strip()
    return "<" not in valor and ">" not in valor


class ProveedorcrearForm(ValidationFormMixin, forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = [
            "nit",
            "nombre_proveedor",
            "telefono_proveedor",
            "correo_proveedor",
            "direccion_proveedor",
        ]
        widgets = {
            "nit": forms.TextInput(attrs={"class": "form-control", "required": True, "maxlength": "15"}),
            "nombre_proveedor": forms.TextInput(attrs={"class": "form-control", "required": True}),
            "telefono_proveedor": forms.TextInput(attrs={"class": "form-control", "required": True, "maxlength": "10"}),
            "correo_proveedor": forms.EmailInput(attrs={"class": "form-control", "required": True}),
            "estado": forms.Select(attrs={"class": "form-select"}),
            "direccion_proveedor": forms.TextInput(attrs={"class": "form-control", "required": True}),
        }

    def clean_nit(self):
        nit = (self.cleaned_data.get("nit") or "").strip()
        if not nit:
            raise forms.ValidationError("El NIT es obligatorio.")
        if not _sin_signos_peligrosos(nit):
            raise forms.ValidationError("El NIT no puede contener signos especiales.")
        if not _solo_numeros(nit):
            raise forms.ValidationError("El NIT solo debe contener numeros.")
        if len(nit) < 7 or len(nit) > 15:
            raise forms.ValidationError("El NIT debe tener entre 7 y 15 digitos.")
        return nit

    def clean_nombre_proveedor(self):
        nombre = (self.cleaned_data.get("nombre_proveedor") or "").strip()
        if not nombre:
            raise forms.ValidationError("El nombre del proveedor es obligatorio.")
        if not _sin_signos_peligrosos(nombre):
            raise forms.ValidationError("El nombre no puede contener signos especiales.")
        if not _solo_letras_y_espacios(nombre):
            raise forms.ValidationError("El nombre del proveedor solo debe contener letras y espacios.")
        return nombre.title()

    def clean_telefono_proveedor(self):
        telefono = (self.cleaned_data.get("telefono_proveedor") or "").strip()
        if not telefono:
            raise forms.ValidationError("El telefono es obligatorio.")
        if not _sin_signos_peligrosos(telefono):
            raise forms.ValidationError("El telefono no puede contener signos especiales.")
        if not _solo_numeros(telefono):
            raise forms.ValidationError("El telefono solo debe contener numeros.")
        if len(telefono) != 10:
            raise forms.ValidationError("El telefono debe tener exactamente 10 digitos.")
        return telefono

    def clean_direccion_proveedor(self):
        direccion = (self.cleaned_data.get("direccion_proveedor") or "").strip()
        if not direccion:
            raise forms.ValidationError("La direccion es obligatoria.")
        if not _sin_signos_peligrosos(direccion):
            raise forms.ValidationError("La direccion no puede contener signos HTML.")
        if any(not (ch.isalnum() or ch.isspace()) for ch in direccion):
            raise forms.ValidationError("La direccion solo puede contener letras, numeros y espacios.")
        return direccion.title()


class ProveedoreditarForm(ProveedorcrearForm):
    class Meta(ProveedorcrearForm.Meta):
        fields = [
            "nit",
            "nombre_proveedor",
            "telefono_proveedor",
            "correo_proveedor",
            "direccion_proveedor",
            "estado",
        ]
