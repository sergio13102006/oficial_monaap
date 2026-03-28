from django import forms
from .models import Producto
from core.form_validations import ValidationFormMixin
import re


def _solo_letras_y_espacios(valor):
    valor = (valor or "").strip()
    return bool(valor) and all(ch.isalpha() or ch.isspace() for ch in valor)


def _solo_letras_numeros_y_espacios(valor):
    valor = (valor or "").strip()
    return bool(valor) and all(ch.isalnum() or ch.isspace() for ch in valor)


def _solo_numeros(valor):
    valor = (valor or "").strip()
    return bool(valor) and valor.isdigit()


def _sin_signos_peligrosos(valor):
    valor = (valor or "").strip()
    return "<" not in valor and ">" not in valor


class ProductoForm(ValidationFormMixin, forms.ModelForm):
    precio = forms.CharField(
        label="Precio",
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "inputmode": "numeric",
                "autocomplete": "off",
                "placeholder": "0",
                "data-format-money": "1",
            }
        ),
    )

    marca_texto = forms.CharField(
        label="Marca",
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Escribe la marca (Ej: Mona Keratina)",
            }
        ),
    )
    unidad_medida = forms.ChoiceField(
        label="Unidad de Medida",
        choices=[("", "Seleccione una unidad")] + list(Producto.UNIDAD_MEDIDA_CHOICES),
        required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = Producto
        fields = [
            "marca",
            "nombre",
            "precio",
            "descripcion",
            "linea",
            "presentacion",
            "unidad_medida",
            "activo",
            "imagen",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Shampoo 500ml"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "linea": forms.TextInput(attrs={"class": "form-control"}),
            "presentacion": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "inputmode": "numeric",
                    "pattern": "[0-9]*",
                    "title": "Solo se permiten numeros",
                    "data-validate": "numeric",
                }
            ),
            "activo": forms.CheckboxInput(attrs={"class": "switch-input"}),
            "marca": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Escribe la marca (Ej: Mona Keratina)"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == "activo":
                continue
            if not field.widget.attrs.get("class"):
                if field.widget.__class__.__name__ in ["Select", "SelectMultiple"]:
                    field.widget.attrs["class"] = "form-select"
                else:
                    field.widget.attrs["class"] = "form-control"

    def clean_nombre(self):
        nombre = self.cleaned_data.get("nombre", "").strip().title()

        if not _sin_signos_peligrosos(nombre):
            raise forms.ValidationError("El nombre no puede contener signos especiales.")
        if not _solo_letras_numeros_y_espacios(nombre):
            raise forms.ValidationError("El nombre solo puede contener letras, numeros y espacios.")
        if not any(c.isalpha() for c in nombre):
            raise forms.ValidationError("El nombre debe contener al menos una letra.")

        if Producto.objects.exclude(pk=self.instance.pk).filter(nombre__iexact=nombre).exists():
            raise forms.ValidationError("Ya existe un producto con este nombre.")

        return nombre

    def clean_marca(self):
        marca = self.cleaned_data.get("marca", "").strip().title()
        if marca and not _sin_signos_peligrosos(marca):
            raise forms.ValidationError("La marca no puede contener signos especiales.")
        if marca and not _solo_letras_y_espacios(marca):
            raise forms.ValidationError("La marca solo puede contener letras y espacios.")
        return marca

    def clean_linea(self):
        linea = self.cleaned_data.get("linea", "").strip().title()
        if not linea:
            return linea
        if not _sin_signos_peligrosos(linea):
            raise forms.ValidationError("La linea no puede contener signos especiales.")
        if not _solo_letras_y_espacios(linea):
            raise forms.ValidationError("La linea solo puede contener letras y espacios.")
        return linea

    def clean_presentacion(self):
        presentacion = self.cleaned_data.get("presentacion", "").strip()
        if not presentacion:
            return presentacion
        if not _sin_signos_peligrosos(presentacion):
            raise forms.ValidationError("La presentacion no puede contener signos especiales.")
        if not _solo_numeros(presentacion):
            raise forms.ValidationError("La presentacion solo puede contener numeros.")
        return presentacion

    def clean_precio(self):
        precio = self.cleaned_data.get("precio")
        precio_str = str(precio or "").strip()

        if not precio_str:
            raise forms.ValidationError("El precio es obligatorio.")

        if re.search(r"[^\d\s\.,]", precio_str):
            raise forms.ValidationError("El precio solo puede contener numeros.")

        normalizado = precio_str.replace(".", "").replace(",", "").replace(" ", "")
        if not normalizado.isdigit():
            raise forms.ValidationError("El precio solo puede contener numeros.")

        return int(normalizado)

    def clean_descripcion(self):
        descripcion = self.cleaned_data.get("descripcion", "").strip()
        if not descripcion:
            return descripcion
        if not _sin_signos_peligrosos(descripcion):
            raise forms.ValidationError("La descripcion no puede contener signos de HTML.")
        return descripcion

    def clean(self):
        cleaned = super().clean()
        unidad_medida = cleaned.get("unidad_medida")

        if not unidad_medida:
            self.add_error("unidad_medida", "La unidad de medida es obligatoria.")

        return cleaned
