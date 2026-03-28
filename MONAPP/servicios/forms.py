from django import forms
from core.form_validations import ValidationFormMixin
from .models import Servicio


def _solo_letras_numeros_y_espacios(valor):
    valor = (valor or "").strip()
    return bool(valor) and all(ch.isalnum() or ch.isspace() for ch in valor)


def _texto_seguro(valor):
    valor = (valor or "").strip()
    return "<" not in valor and ">" not in valor


def _nombre_servicio_duplicado(nombre, servicio_id=None):
    qs = Servicio.objects.filter(nombre__iexact=nombre.strip())
    if servicio_id:
        qs = qs.exclude(pk=servicio_id)
    return qs.exists()


class ServicioForm(ValidationFormMixin, forms.ModelForm):
    class Meta:
        model = Servicio
        fields = ["nombre", "precio", "descripcion", "imagen", "video", "activo"]
        widgets = {
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nombre del servicio",
                    "autocomplete": "off",
                    "data-validate": "alnum",
                }
            ),
            "precio": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "Precio",
                    "inputmode": "decimal",
                    "data-validate": "money",
                }
            ),
            "descripcion": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Descripción del servicio",
                    "data-validate": "text",
                }
            ),
            "imagen": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                }
            ),
            "video": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "video/*",
                }
            ),
            "activo": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }
        labels = {
            "nombre": "Nombre del Servicio",
            "precio": "Precio ($)",
            "descripcion": "Descripción",
            "imagen": "Imagen del Servicio",
            "video": "Video del Servicio",
            "activo": "Activo",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # En edición normalmente no obligas a volver a subir archivos
        if "imagen" in self.fields:
            self.fields["imagen"].required = False

        if "video" in self.fields:
            self.fields["video"].required = False

        if "activo" in self.fields:
            self.fields["activo"].required = False

    def clean_nombre(self):
        nombre = (self.cleaned_data.get("nombre") or "").strip()

        if not nombre:
            raise forms.ValidationError("El nombre del servicio es obligatorio.")

        if not _texto_seguro(nombre):
            raise forms.ValidationError("El nombre no puede contener los signos < o >.")

        if not _solo_letras_numeros_y_espacios(nombre):
            raise forms.ValidationError("El nombre solo puede contener letras, números y espacios.")

        servicio_id = getattr(self.instance, "pk", None)
        if _nombre_servicio_duplicado(nombre, servicio_id):
            raise forms.ValidationError("Ya existe un servicio con este nombre.")

        return " ".join(nombre.split())

    def clean_precio(self):
        precio = self.cleaned_data.get("precio")

        if precio is None:
            raise forms.ValidationError("El precio es obligatorio.")

        if precio < 0:
            raise forms.ValidationError("El precio no puede ser negativo.")

        return precio

    def clean_descripcion(self):
        descripcion = (self.cleaned_data.get("descripcion") or "").strip()

        if not descripcion:
            raise forms.ValidationError("La descripción es obligatoria.")

        if len(descripcion) < 10:
            raise forms.ValidationError("La descripción debe tener al menos 10 caracteres.")

        if not _texto_seguro(descripcion):
            raise forms.ValidationError("La descripción no puede contener los signos < o >.")

        return descripcion

    def clean_imagen(self):
        imagen = self.cleaned_data.get("imagen")

        if imagen:
            content_type = getattr(imagen, "content_type", "")
            if content_type and not content_type.startswith("image/"):
                raise forms.ValidationError("Debes subir un archivo de imagen válido.")

        return imagen

    def clean_video(self):
        video = self.cleaned_data.get("video")

        if video:
            content_type = getattr(video, "content_type", "")
            if content_type and not content_type.startswith("video/"):
                raise forms.ValidationError("Debes subir un archivo de video válido.")

        return video
