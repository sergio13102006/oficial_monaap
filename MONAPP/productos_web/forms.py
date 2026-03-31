import re
from decimal import Decimal
from django import forms
from core.form_validations import ValidationFormMixin
from .models import ProductoWeb
from PIL import Image, UnidentifiedImageError


def _nombre_producto_duplicado(nombre, producto_id=None):
    qs = ProductoWeb.objects.filter(nombre__iexact=nombre)
    if producto_id:
        qs = qs.exclude(pk=producto_id)
    return qs.exists()


class ProductoWebForm(ValidationFormMixin, forms.ModelForm):
    class Meta:
        model = ProductoWeb
        fields = ['nombre', 'precio', 'descripcion', 'imagen', 'visible']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del producto',
                'maxlength': '200',
            }),
            'precio': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 25000',
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Descripción breve del producto…',
                'maxlength': '500',
            }),
            'imagen': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/jpeg,image/png,image/webp,image/gif',
            }),
            'visible': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }
        labels = {
            'nombre': 'Nombre',
            'precio': 'Precio Público (COP)',
            'descripcion': 'Descripción',
            'imagen': 'Imagen del Producto',
            'visible': 'Visible en la Web',
        }

    # ── Nombre ──────────────────────────────────────────────────────────
    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre', '').strip()
        if not nombre:
            raise forms.ValidationError('El nombre es obligatorio.')
        if len(nombre) < 2:
            raise forms.ValidationError('El nombre debe tener al menos 2 caracteres.')
        if len(nombre) > 200:
            raise forms.ValidationError('El nombre no puede superar 200 caracteres.')
        if any(ch in nombre for ch in ('<', '>', '`', '{', '}', '[', ']', ';')):
            raise forms.ValidationError(
                'El nombre contiene caracteres no permitidos.'
            )
        # Solo letras (incluye tildes/ñ), números, espacios y algunos especiales
        if not re.match(
            r'^[a-zA-ZáéíóúÁÉÍÓÚàèìòùÀÈÌÒÙñÑüÜ0-9\s\-\.\,\(\)\&\+\/\#\*\!\?\:\'"]+$',
            nombre
        ):
            raise forms.ValidationError(
                'El nombre contiene caracteres no permitidos. Use letras, números y los símbolos -.,()&+/#*!?:.\'"'
            )
        producto_id = getattr(self.instance, 'pk', None)
        if _nombre_producto_duplicado(nombre, producto_id):
            raise forms.ValidationError('Ya existe un producto con este nombre.')
        return nombre

    # ── Precio COP ──────────────────────────────────────────────────────
    def clean_precio(self):
        precio = self.cleaned_data.get('precio')
        if precio is None:
            raise forms.ValidationError('El precio es obligatorio.')
        if precio < Decimal('100'):
            raise forms.ValidationError(
                'El precio mínimo es $100 COP. '
                'Los precios en Colombia se expresan en pesos enteros.'
            )
        if precio > Decimal('99999999'):
            raise forms.ValidationError('El precio no puede superar $99.999.999 COP.')
        # Sin decimales en pesos colombianos
        if precio != precio.quantize(Decimal('1')):
            raise forms.ValidationError(
                'El precio debe ser un valor entero en pesos colombianos (sin centavos).'
            )
        return precio

    # ── Descripción ─────────────────────────────────────────────────────
    def clean_descripcion(self):
        desc = self.cleaned_data.get('descripcion', '').strip()
        if len(desc) > 500:
            raise forms.ValidationError(
                f'La descripción no puede superar 500 caracteres (actualmente {len(desc)}).'
            )
        return desc

    # ── Imagen ───────────────────────────────────────────────────────────
    def clean_imagen(self):
        imagen = self.cleaned_data.get('imagen')
        if imagen and hasattr(imagen, 'size'):
            max_bytes = 5 * 1024 * 1024  # 5 MB
            if imagen.size > max_bytes:
                size_mb = imagen.size / (1024 * 1024)
                raise forms.ValidationError(
                    f'La imagen pesa {size_mb:.1f} MB. El máximo permitido es 5 MB.'
                )
            tipos_validos = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
            if hasattr(imagen, 'content_type') and imagen.content_type not in tipos_validos:
                raise forms.ValidationError(
                    'Formato no válido. Solo se permiten imágenes JPG, PNG, WEBP o GIF.'
                )

            try:
                imagen.seek(0)
                with Image.open(imagen) as im:
                    im.verify()
                imagen.seek(0)
            except (UnidentifiedImageError, OSError):
                raise forms.ValidationError("El archivo no es una imagen válida o está corrupto.")
        return imagen
    
