import re
from datetime import date, timedelta
from decimal import Decimal

from django import forms

from core.form_validations import ValidationFormMixin
from .models import Promocion
from PIL import Image, UnidentifiedImageError


def _nombre_promocion_duplicado(nombre, promocion_id=None):
    qs = Promocion.objects.filter(nombre__iexact=nombre)
    if promocion_id:
        qs = qs.exclude(pk=promocion_id)
    return qs.exists()


class PromocionForm(ValidationFormMixin, forms.ModelForm):
    @staticmethod
    def get_date_limits():
        today = date.today()
        return today - timedelta(days=365), today + timedelta(days=365)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        min_date, max_date = self.get_date_limits()
        self.fields["fecha_inicio"].widget.attrs.update({
            "min": min_date.isoformat(),
            "max": max_date.isoformat(),
        })
        self.fields["fecha_fin"].widget.attrs.update({
            "min": min_date.isoformat(),
            "max": max_date.isoformat(),
        })
        self.fields["fecha_inicio"].widget.attrs.pop("data-validate", None)
        self.fields["fecha_fin"].widget.attrs.pop("data-validate", None)

    class Meta:
        model = Promocion
        fields = [
            "nombre",
            "descripcion",
            "etiqueta",
            "porcentaje_descuento",
            "fecha_inicio",
            "fecha_fin",
            "imagen",
            "activa",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nombre de la promocion",
                "maxlength": "200",
            }),
            "descripcion": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Texto breve para la tarjeta publica...",
                "maxlength": "500",
            }),
            "etiqueta": forms.Select(attrs={
                "class": "form-select",
            }),
            "porcentaje_descuento": forms.TextInput(attrs={
                "class": "form-control",
                "inputmode": "numeric",
                "placeholder": "Ej: 15",
            }),
            "fecha_inicio": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "fecha_fin": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "imagen": forms.ClearableFileInput(attrs={
                "class": "form-control",
                "accept": "image/jpeg,image/png,image/webp,image/gif",
            }),
            "activa": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
        }
        labels = {
            "nombre": "Nombre",
            "descripcion": "Descripcion",
            "etiqueta": "Etiqueta",
            "porcentaje_descuento": "Descuento (%)",
            "fecha_inicio": "Fecha de Inicio",
            "fecha_fin": "Fecha de Fin",
            "imagen": "Imagen de la Promocion",
            "activa": "Activa",
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get("nombre", "").strip()
        if not nombre:
            raise forms.ValidationError("El nombre es obligatorio.")
        if len(nombre) < 2:
            raise forms.ValidationError("El nombre debe tener al menos 2 caracteres.")
        if len(nombre) > 200:
            raise forms.ValidationError("El nombre no puede superar 200 caracteres.")
        if not re.match(r"^[a-zA-ZáéíóúÁÉÍÓÚàèìòùÀÈÌÒÙñÑüÜ\s]+$", nombre):
            raise forms.ValidationError(
                "El nombre solo puede contener letras y espacios. No se permiten numeros ni caracteres especiales."
            )
        promocion_id = getattr(self.instance, "pk", None)
        if _nombre_promocion_duplicado(nombre, promocion_id):
            raise forms.ValidationError("Ya existe una promocion con este nombre.")
        return nombre

    def clean_descripcion(self):
        desc = self.cleaned_data.get("descripcion", "").strip()
        if len(desc) > 500:
            raise forms.ValidationError(
                f"La descripcion no puede superar 500 caracteres (actualmente {len(desc)})."
            )
        return desc

    def clean_porcentaje_descuento(self):
        pct = self.cleaned_data.get("porcentaje_descuento")
        if pct is None:
            raise forms.ValidationError("El porcentaje de descuento es obligatorio.")
        if pct < Decimal("1"):
            raise forms.ValidationError("El descuento minimo es 1%.")
        if pct > Decimal("100"):
            raise forms.ValidationError("El descuento no puede superar el 100%.")
        if pct != pct.quantize(Decimal("0.01")):
            raise forms.ValidationError("El descuento admite maximo 2 decimales.")
        return pct

    def clean_fecha_inicio(self):
        fecha = self.cleaned_data.get("fecha_inicio")
        if not fecha:
            raise forms.ValidationError("La fecha de inicio es obligatoria.")
        min_date, max_date = self.get_date_limits()
        if fecha < min_date or fecha > max_date:
            raise forms.ValidationError(
                f"La fecha de inicio debe estar entre {min_date.strftime('%d/%m/%Y')} y {max_date.strftime('%d/%m/%Y')}."
            )
        return fecha

    def clean_fecha_fin(self):
        fecha = self.cleaned_data.get("fecha_fin")
        if not fecha:
            raise forms.ValidationError("La fecha de fin es obligatoria.")
        min_date, max_date = self.get_date_limits()
        if fecha < min_date or fecha > max_date:
            raise forms.ValidationError(
                f"La fecha de fin debe estar entre {min_date.strftime('%d/%m/%Y')} y {max_date.strftime('%d/%m/%Y')}."
            )
        return fecha

    def clean_imagen(self):
        imagen = self.cleaned_data.get("imagen")
        if imagen and hasattr(imagen, "size"):
            max_bytes = 5 * 1024 * 1024
            if imagen.size > max_bytes:
                size_mb = imagen.size / (1024 * 1024)
                raise forms.ValidationError(
                    f"La imagen pesa {size_mb:.1f} MB. El maximo permitido es 5 MB."
                )
            tipos_validos = ["image/jpeg", "image/png", "image/webp", "image/gif"]
            if hasattr(imagen, "content_type") and imagen.content_type not in tipos_validos:
                raise forms.ValidationError(
                    "Formato no valido. Solo se permiten imagenes JPG, PNG, WEBP o GIF."
                )

            try:
                imagen.seek(0)
                with Image.open(imagen) as im:
                    im.verify()
                imagen.seek(0)
            except (UnidentifiedImageError, OSError):
                raise forms.ValidationError("El archivo no es una imagen válida o está corrupto.")
        return imagen

    def clean(self):
        cleaned_data = super().clean()
        inicio = cleaned_data.get("fecha_inicio")
        fin = cleaned_data.get("fecha_fin")

        if inicio and fin and fin < inicio:
            self.add_error("fecha_fin", "La fecha de fin no puede ser anterior a la fecha de inicio.")

        return cleaned_data
