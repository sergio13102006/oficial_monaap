from django import forms
from .models import Venta

class VentaForm(forms.ModelForm):
    class Meta:
        model = Venta
        fields = ["cliente"]
        
        widgets = {
            'cliente': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_cliente'
            }),
        }
