import uuid

from django import forms

from .models import CuentaFinanciera


class CuentaFinancieraForm(forms.ModelForm):
    class Meta:
        model = CuentaFinanciera
        fields = ["nombre", "tipo", "activa", "orden_visual"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Caja Principal o Bancolombia"}),
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "activa": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "orden_visual": forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": 1}),
        }

    def clean_nombre(self):
        nombre = (self.cleaned_data.get("nombre") or "").strip()
        if not nombre:
            raise forms.ValidationError("Ingresa el nombre de la cuenta financiera.")
        nombre = " ".join(nombre.split())
        return nombre.title()


class TransferenciaCuentaForm(forms.Form):
    fecha = forms.DateField(
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"})
    )
    cuenta_origen = forms.ModelChoiceField(
        queryset=CuentaFinanciera.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    cuenta_destino = forms.ModelChoiceField(
        queryset=CuentaFinanciera.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    valor = forms.DecimalField(
        min_value=1,
        max_digits=18,
        decimal_places=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 1, "step": 1}),
    )
    observacion = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )
    request_uid = forms.CharField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cuentas = CuentaFinanciera.objects.filter(activa=True).order_by("orden_visual", "nombre")
        self.fields["cuenta_origen"].queryset = cuentas
        self.fields["cuenta_destino"].queryset = cuentas
        self.fields["request_uid"].initial = self.initial.get("request_uid") or str(uuid.uuid4())

    def clean(self):
        cleaned_data = super().clean()
        origen = cleaned_data.get("cuenta_origen")
        destino = cleaned_data.get("cuenta_destino")
        if origen and destino and origen.pk == destino.pk:
            raise forms.ValidationError("La cuenta origen y la cuenta destino deben ser distintas.")
        return cleaned_data


class BaseDiariaCuentaForm(forms.Form):
    fecha = forms.DateField(
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"})
    )
    cuenta = forms.ModelChoiceField(
        queryset=CuentaFinanciera.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    base_inicial = forms.DecimalField(
        min_value=0,
        max_digits=18,
        decimal_places=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": 1}),
    )
    observacion = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cuenta"].queryset = CuentaFinanciera.objects.filter(activa=True).order_by(
            "orden_visual", "nombre"
        )
