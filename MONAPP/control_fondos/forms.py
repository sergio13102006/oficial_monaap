import uuid

from django import forms

from clientes.models import Cliente
from personal.models import Personal

from .models import CuentaFinanciera, MovimientoCuenta, JornadaDiaria, _normalize_text


class CuentaFinancieraForm(forms.ModelForm):
    class Meta:
        model = CuentaFinanciera
        fields = [
            "codigo",
            "nombre",
            "tipo",
            "categoria_operativa",
            "activa",
            "obligatoria_apertura",
            "requiere_base_inicial",
            "requiere_referencia",
            "permite_entradas",
            "permite_salidas",
            "orden_visual",
        ]
        widgets = {
            "codigo": forms.TextInput(attrs={"class": "form-control", "placeholder": "Se genera automáticamente si se deja vacío"}),
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Caja Principal o Bancolombia"}),
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "categoria_operativa": forms.Select(attrs={"class": "form-select"}),
            "activa": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "obligatoria_apertura": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "requiere_base_inicial": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "requiere_referencia": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "permite_entradas": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "permite_salidas": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "orden_visual": forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": 1}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria_operativa"].required = False

    def clean_codigo(self):
        codigo = (self.cleaned_data.get("codigo") or "").strip()
        if not codigo:
            return codigo
        return " ".join(codigo.split()).upper().replace(" ", "_")

    def clean_nombre(self):
        nombre = (self.cleaned_data.get("nombre") or "").strip()
        if not nombre:
            raise forms.ValidationError("Ingresa el nombre de la cuenta financiera.")
        nombre = " ".join(nombre.split())
        normalizado = _normalize_text(nombre)
        if CuentaFinanciera.objects.exclude(pk=self.instance.pk).filter(nombre_normalizado=normalizado).exists():
            raise forms.ValidationError("Ya existe una cuenta con un nombre equivalente.")
        return nombre.title()

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("codigo"):
            cleaned_data["codigo"] = None
        categoria = cleaned_data.get("categoria_operativa") or ""
        if not categoria:
            tipo = cleaned_data.get("tipo")
            categoria = {
                CuentaFinanciera.TIPO_EFECTIVO: CuentaFinanciera.CATEGORIA_CAJA,
                CuentaFinanciera.TIPO_CAJA_FUERTE: CuentaFinanciera.CATEGORIA_CAJA_FUERTE,
                CuentaFinanciera.TIPO_BANCO: CuentaFinanciera.CATEGORIA_BANCO,
                CuentaFinanciera.TIPO_BILLETERA: CuentaFinanciera.CATEGORIA_BILLETERA,
                CuentaFinanciera.TIPO_DATAFONO: CuentaFinanciera.CATEGORIA_MEDIO_PAGO,
                CuentaFinanciera.TIPO_FINANCIACION: CuentaFinanciera.CATEGORIA_FINANCIACION,
                CuentaFinanciera.TIPO_TARJETA: CuentaFinanciera.CATEGORIA_EGRESO,
            }.get(tipo, CuentaFinanciera.CATEGORIA_OTRA)
            cleaned_data["categoria_operativa"] = categoria
        if categoria in {
            CuentaFinanciera.CATEGORIA_MEDIO_PAGO,
            CuentaFinanciera.CATEGORIA_FINANCIACION,
            CuentaFinanciera.CATEGORIA_EGRESO,
        }:
            cleaned_data["requiere_base_inicial"] = False
            cleaned_data["obligatoria_apertura"] = False
        if categoria == CuentaFinanciera.CATEGORIA_EGRESO:
            cleaned_data["permite_entradas"] = False
        return cleaned_data


class AperturaJornadaForm(forms.ModelForm):
    class Meta:
        model = JornadaDiaria
        fields = ["fecha", "sede", "base_inicial_caja", "base_inicial_caja_fuerte", "observacion_apertura"]
        widgets = {
            "fecha": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "sede": forms.TextInput(attrs={"class": "form-control", "placeholder": "Sede o punto de venta"}),
            "base_inicial_caja": forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": 1}),
            "base_inicial_caja_fuerte": forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": 1}),
            "observacion_apertura": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class CierreJornadaForm(forms.Form):
    fecha = forms.DateField(widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}))
    efectivo_contado_real = forms.DecimalField(
        min_value=0,
        max_digits=18,
        decimal_places=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": 1}),
    )
    caja_fuerte_contada_real = forms.DecimalField(
        min_value=0,
        max_digits=18,
        decimal_places=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": 1}),
    )
    transferencias_verificadas = forms.DecimalField(
        min_value=0,
        max_digits=18,
        decimal_places=0,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": 1}),
    )
    datofono_verificado = forms.DecimalField(
        min_value=0,
        max_digits=18,
        decimal_places=0,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": 1}),
    )
    financiacion_verificada = forms.DecimalField(
        min_value=0,
        max_digits=18,
        decimal_places=0,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": 1}),
    )
    observacion_cierre = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )
    autorizacion_supervisor = forms.BooleanField(required=False)
    confirmacion = forms.BooleanField(required=True, label="Confirmo que revisé y deseo cerrar el día")


class ReaperturaJornadaForm(forms.Form):
    fecha = forms.DateField(widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}))
    motivo = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )


class MovimientoControladoForm(forms.Form):
    fecha = forms.DateField(widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}))
    tipo_movimiento = forms.ChoiceField(
        choices=MovimientoCuenta.TIPOS_MOVIMIENTO,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    cuenta = forms.ModelChoiceField(
        queryset=CuentaFinanciera.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    procedimiento = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Procedimiento"}),
    )
    producto_servicio = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Producto o servicio"}),
    )
    profesional = forms.ModelChoiceField(
        queryset=Personal.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    valor_total = forms.DecimalField(
        min_value=0,
        max_digits=18,
        decimal_places=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": 1}),
    )
    descuento = forms.DecimalField(
        min_value=0,
        max_digits=18,
        decimal_places=0,
        required=False,
        initial=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": 1}),
    )
    entrada_efectivo = forms.DecimalField(
        min_value=0,
        max_digits=18,
        decimal_places=0,
        required=False,
        initial=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": 1}),
    )
    salida_efectivo = forms.DecimalField(
        min_value=0,
        max_digits=18,
        decimal_places=0,
        required=False,
        initial=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": 1}),
    )
    bancolombia = forms.DecimalField(
        min_value=0,
        max_digits=18,
        decimal_places=0,
        required=False,
        initial=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": 1}),
    )
    nequi = forms.DecimalField(
        min_value=0,
        max_digits=18,
        decimal_places=0,
        required=False,
        initial=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": 1}),
    )
    daviplata = forms.DecimalField(
        min_value=0,
        max_digits=18,
        decimal_places=0,
        required=False,
        initial=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": 1}),
    )
    nubank = forms.DecimalField(
        min_value=0,
        max_digits=18,
        decimal_places=0,
        required=False,
        initial=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": 1}),
    )
    datofono = forms.DecimalField(
        min_value=0,
        max_digits=18,
        decimal_places=0,
        required=False,
        initial=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": 1}),
    )
    sistecredito_addi = forms.DecimalField(
        min_value=0,
        max_digits=18,
        decimal_places=0,
        required=False,
        initial=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": 1}),
    )
    ingreso_caja_fuerte = forms.DecimalField(
        min_value=0,
        max_digits=18,
        decimal_places=0,
        required=False,
        initial=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": 1}),
    )
    retiro_caja_fuerte = forms.DecimalField(
        min_value=0,
        max_digits=18,
        decimal_places=0,
        required=False,
        initial=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": 1}),
    )
    tarjeta_credito_compras = forms.DecimalField(
        min_value=0,
        max_digits=18,
        decimal_places=0,
        required=False,
        initial=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": 1}),
    )
    motivo_salida = forms.ChoiceField(
        choices=[
            ("", "Seleccione"),
            ("COMPRA_DE_INSUMOS", "Compra de insumos"),
            ("DEVOLUCION_CLIENTE", "Devolución a cliente"),
            ("PAGO_PROVEEDOR", "Pago a proveedor"),
            ("GASTO_OPERATIVO", "Gasto operativo"),
            ("TRASLADO_CAJA_FUERTE", "Traslado a caja fuerte"),
            ("AJUSTE_AUTORIZADO", "Ajuste autorizado"),
            ("OTRO", "Otro"),
        ],
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    motivo_otro = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Explica el motivo si elegiste Otro"}),
    )
    referencia = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Referencia o comprobante"}),
    )
    comprobante = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Soporte"}),
    )
    soporte_adjunto = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
    )
    observacion = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cuentas = CuentaFinanciera.objects.filter(activa=True).order_by("orden_visual", "nombre")
        self.fields["cuenta"].queryset = cuentas
        self.fields["profesional"].queryset = Personal.objects.all().order_by("id")
        self.fields["cliente"].queryset = Cliente.objects.all().order_by("id")

    def clean(self):
        cleaned_data = super().clean()
        tipo_movimiento = cleaned_data.get("tipo_movimiento")
        valor_total = cleaned_data.get("valor_total") or 0
        descuento = cleaned_data.get("descuento") or 0
        valor_neto = valor_total - descuento
        if valor_neto < 0:
            raise forms.ValidationError("El valor neto no puede ser negativo.")

        cleaned_data["valor_neto"] = valor_neto

        medios_ingreso = [
            "entrada_efectivo",
            "bancolombia",
            "nequi",
            "daviplata",
            "nubank",
            "datofono",
            "sistecredito_addi",
        ]
        medios_egreso = [
            "salida_efectivo",
            "tarjeta_credito_compras",
        ]
        medios_traslado = [
            "ingreso_caja_fuerte",
            "retiro_caja_fuerte",
        ]

        total_ingreso = sum((cleaned_data.get(field) or 0) for field in medios_ingreso)
        total_egreso = sum((cleaned_data.get(field) or 0) for field in medios_egreso)
        total_traslado = sum((cleaned_data.get(field) or 0) for field in medios_traslado)

        if tipo_movimiento == MovimientoCuenta.TIPO_MOVIMIENTO_INGRESO:
            if total_ingreso <= 0:
                raise forms.ValidationError("Debes registrar al menos un medio de pago para el ingreso.")
            if total_ingreso != valor_neto:
                raise forms.ValidationError("El valor neto debe coincidir con la suma de los medios de pago.")
            if total_egreso > 0 or total_traslado > 0:
                raise forms.ValidationError("Un ingreso no puede mezclar medios de salida o traslados internos.")

        if tipo_movimiento in {
            MovimientoCuenta.TIPO_MOVIMIENTO_SALIDA,
            MovimientoCuenta.TIPO_MOVIMIENTO_COMPRA_TARJETA,
        }:
            if total_egreso <= 0:
                raise forms.ValidationError("Debes registrar al menos una salida o compra con tarjeta.")
            if total_egreso != valor_neto:
                raise forms.ValidationError("El valor neto debe coincidir con la suma de las salidas registradas.")
            if total_ingreso > 0 or total_traslado > 0:
                raise forms.ValidationError("Una salida no puede mezclar medios de ingreso o traslados internos.")

        if tipo_movimiento == MovimientoCuenta.TIPO_MOVIMIENTO_TRANSFERENCIA:
            total_transferencia = total_traslado or total_ingreso
            if total_transferencia <= 0:
                raise forms.ValidationError("Debes registrar el valor de la transferencia.")
            if total_transferencia != valor_neto:
                raise forms.ValidationError("El valor neto debe coincidir con el valor de la transferencia.")

        if tipo_movimiento == MovimientoCuenta.TIPO_MOVIMIENTO_AJUSTE:
            total_ajuste = total_ingreso + total_egreso + total_traslado
            if total_ajuste <= 0:
                raise forms.ValidationError("Debes registrar un valor para el ajuste.")
            if total_ajuste != valor_neto:
                raise forms.ValidationError("El valor neto debe coincidir con el ajuste registrado.")

        total_medios = (
            (cleaned_data.get("entrada_efectivo") or 0)
            + (cleaned_data.get("bancolombia") or 0)
            + (cleaned_data.get("nequi") or 0)
            + (cleaned_data.get("daviplata") or 0)
            + (cleaned_data.get("nubank") or 0)
            + (cleaned_data.get("datofono") or 0)
            + (cleaned_data.get("sistecredito_addi") or 0)
        )

        if tipo_movimiento == MovimientoCuenta.TIPO_MOVIMIENTO_INGRESO and total_medios != valor_neto:
            raise forms.ValidationError("El valor neto debe coincidir con la suma de los medios de pago.")

        if tipo_movimiento in {
            MovimientoCuenta.TIPO_MOVIMIENTO_SALIDA,
            MovimientoCuenta.TIPO_MOVIMIENTO_COMPRA_TARJETA,
        }:
            if not cleaned_data.get("motivo_salida"):
                raise forms.ValidationError("Las salidas y compras con tarjeta requieren motivo.")

        if any(
            cleaned_data.get(field)
            for field in ["bancolombia", "nequi", "daviplata", "nubank", "datofono", "sistecredito_addi"]
        ) and not cleaned_data.get("referencia"):
            raise forms.ValidationError("Los pagos electrónicos requieren referencia.")

        if cleaned_data.get("motivo_salida") == "OTRO" and not cleaned_data.get("motivo_otro"):
            raise forms.ValidationError("Si seleccionas Otro, debes explicar el motivo.")

        cuenta = cleaned_data.get("cuenta")
        if cuenta:
            if tipo_movimiento == MovimientoCuenta.TIPO_MOVIMIENTO_INGRESO and not cuenta.permite_entradas:
                raise forms.ValidationError(f"La cuenta {cuenta.nombre} no permite entradas.")
            if tipo_movimiento in {
                MovimientoCuenta.TIPO_MOVIMIENTO_SALIDA,
                MovimientoCuenta.TIPO_MOVIMIENTO_COMPRA_TARJETA,
            } and not cuenta.permite_salidas:
                raise forms.ValidationError(f"La cuenta {cuenta.nombre} no permite salidas.")
            if cuenta.requiere_referencia and not cleaned_data.get("referencia"):
                raise forms.ValidationError(f"La cuenta {cuenta.nombre} requiere referencia.")

        return cleaned_data


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
    referencia = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Referencia bancaria"}),
    )
    comprobante = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Comprobante"}),
    )
    soporte_adjunto = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
    )
    observacion = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )
    request_uid = forms.CharField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cuentas = CuentaFinanciera.objects.filter(
            activa=True,
            permite_entradas=True,
            permite_salidas=True,
        ).order_by("orden_visual", "nombre")
        self.fields["cuenta_origen"].queryset = cuentas
        self.fields["cuenta_destino"].queryset = cuentas
        self.fields["request_uid"].initial = self.initial.get("request_uid") or str(uuid.uuid4())

    def clean(self):
        cleaned_data = super().clean()
        origen = cleaned_data.get("cuenta_origen")
        destino = cleaned_data.get("cuenta_destino")
        if origen and destino and origen.pk == destino.pk:
            raise forms.ValidationError("La cuenta origen y la cuenta destino deben ser distintas.")
        if cleaned_data.get("valor") and cleaned_data.get("valor") <= 0:
            raise forms.ValidationError("El valor de la transferencia debe ser mayor que cero.")
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
        self.fields["cuenta"].queryset = CuentaFinanciera.objects.filter(
            activa=True,
            requiere_base_inicial=True,
        ).order_by(
            "orden_visual", "nombre"
        )
