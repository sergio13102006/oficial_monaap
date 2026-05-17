from django import forms
from .models import MovimientoInventario, DetalleMovimiento
from django.forms import inlineformset_factory
from core.form_validations import ValidationFormMixin


class MovimientoInventarioForm(ValidationFormMixin, forms.ModelForm):
    class Meta:
        model = MovimientoInventario
        fields = [
            'proveedor',
            'nombre_repartidor',
            'apellido_repartidor',
            'cedula_repartidor',
            'telefono_repartidor',
            'precio_total',
            'tipo_vehiculo',
            'placa_vehiculo',
            
        ]

DetalleMovimientoFormSet = inlineformset_factory(
    MovimientoInventario,
    DetalleMovimiento,
    fields=['producto', 'cantidad'],
    extra=1,
    can_delete=True
)
