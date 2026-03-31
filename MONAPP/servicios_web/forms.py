import re

from django import forms

from core.form_validations import ValidationFormMixin

from .models import ServicioWeb


_TEXTO_SEGURO_RE = re.compile(r'^[A-Za-z0-9ÁÉÍÓÚáéíóúÑñ\s]+$')


def _texto_seguro(valor: str) -> bool:
    return bool(_TEXTO_SEGURO_RE.match((valor or '').strip()))


class ServicioWebForm(ValidationFormMixin, forms.ModelForm):
    class Meta:
        model = ServicioWeb
        fields = ['nombre', 'descripcion', 'precio', 'imagen', 'video', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del servicio web',
                'maxlength': '200',
                'pattern': r'[A-Za-z0-9ÁÉÍÓÚáéíóúÑñ\s]+',
                'title': 'Solo letras, números y espacios',
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Descripción detallada del servicio web',
            }),
            'precio': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Precio al público',
                'inputmode': 'decimal',
            }),
            'imagen': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'video': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'video/*'
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'nombre': 'Nombre del Servicio Web',
            'descripcion': 'Descripción',
            'precio': 'Precio al público',
            'imagen': 'Imagen del Servicio (opcional)',
            'video': 'Video del Servicio (opcional)',
            'activo': 'Estado del Servicio',
        }

    def clean_nombre(self):
        nombre = (self.cleaned_data.get('nombre') or '').strip()

        if not nombre:
            raise forms.ValidationError('El nombre es obligatorio.')

        if len(nombre) < 3:
            raise forms.ValidationError('Debe tener al menos 3 caracteres.')

        if not _texto_seguro(nombre):
            raise forms.ValidationError('Solo se permiten letras, números y espacios.')

        qs = ServicioWeb.objects.filter(nombre__iexact=nombre)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError('Ya existe un servicio web con ese nombre.')

        return nombre

    def clean_descripcion(self):
        descripcion = (self.cleaned_data.get('descripcion') or '').strip()

        if not descripcion:
            raise forms.ValidationError('La descripción es obligatoria.')

        if len(descripcion) < 10:
            raise forms.ValidationError('Debe tener al menos 10 caracteres.')

        if not _texto_seguro(descripcion):
            raise forms.ValidationError('Solo se permiten letras, números y espacios.')

        return descripcion

    def clean_precio(self):
        precio = self.cleaned_data.get('precio')

        if precio is None:
            raise forms.ValidationError('El precio es obligatorio.')

        if precio <= 0:
            raise forms.ValidationError('El precio debe ser mayor a 0.')

        return precio

    def clean_video(self):
        video = self.cleaned_data.get('video')

        if not video:
            return video

        max_size_mb = 25
        if video.size > max_size_mb * 1024 * 1024:
            raise forms.ValidationError(f'El video no puede superar {max_size_mb} MB.')

        allowed_extensions = ('.mp4', '.webm', '.ogg', '.mov')
        nombre = video.name.lower()
        if not nombre.endswith(allowed_extensions):
            raise forms.ValidationError('Formato de video no permitido.')

        return video
