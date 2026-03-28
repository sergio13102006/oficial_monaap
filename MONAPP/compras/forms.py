import re

from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.db.models import Sum

from .models import (
    Compra,
    DetalleCompra,
    DevolucionCompra,
    DetalleDevolucionCompra,
)
from Proveedores.models import Proveedor
from Productos.models import Producto


MAX_CANTIDAD_COMPRA = 1000000


PATRONES_TEXTO_PELIGROSO = [
    re.compile(r"{{|}}|{%|%}"),
    re.compile(r"<\s*script", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),
]


def validar_texto_seguro(valor, nombre_campo):
    valor = (valor or "").strip()

    if not valor:
        raise forms.ValidationError(f"El campo {nombre_campo} es obligatorio.")

    if any(not (ch.isalnum() or ch.isspace()) for ch in valor):
        raise forms.ValidationError(
            f"El campo {nombre_campo} solo puede contener letras, numeros y espacios."
        )

    for patron in PATRONES_TEXTO_PELIGROSO:
        if patron.search(valor):
            raise forms.ValidationError(
                f"El campo {nombre_campo} contiene patrones no permitidos."
            )

    return valor


class CompraForm(forms.ModelForm):
    class Meta:
        model = Compra
        fields = ["proveedor"]
        widgets = {
            "proveedor": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs_activos = Proveedor.objects.filter(estado="activo")
        proveedor_actual = None

        if self.instance and getattr(self.instance, "proveedor_id", None):
            proveedor_actual = (
                Proveedor.objects
                .filter(pk=self.instance.proveedor_id)
                .first()
            )

        if proveedor_actual:
            qs_activos = (qs_activos | Proveedor.objects.filter(pk=proveedor_actual.pk)).distinct()

        self.fields["proveedor"].queryset = qs_activos.order_by("nombre_proveedor")
        self.fields["proveedor"].label_from_instance = lambda obj: (
            f"{obj.nombre_proveedor} (Inactivo)" if obj.estado != "activo" else obj.nombre_proveedor
        )

        if proveedor_actual and proveedor_actual.estado != "activo":
            self.fields["proveedor"].disabled = True
            self.fields["proveedor"].help_text = "El proveedor actual está inactivo, pero se mantiene por historial de la compra."

    def clean_proveedor(self):
        proveedor = self.cleaned_data.get("proveedor")

        if not proveedor:
            if self.instance and getattr(self.instance, "proveedor_id", None):
                return self.instance.proveedor
            raise forms.ValidationError("Selecciona un proveedor.")

        proveedor_actual = None
        if self.instance and getattr(self.instance, "proveedor_id", None):
            proveedor_actual = Proveedor.objects.filter(pk=self.instance.proveedor_id).first()

        if proveedor_actual and proveedor_actual.estado != "activo":
            if proveedor.pk != proveedor_actual.pk:
                raise forms.ValidationError(
                    "No puedes cambiar el proveedor porque el proveedor original está inactivo."
                )
            return proveedor_actual

        if self.instance and getattr(self.instance, "proveedor_id", None) == proveedor.pk:
            return proveedor

        if proveedor.estado != "activo":
            raise forms.ValidationError(
                "Solo puedes registrar compras con proveedores activos."
            )

        return proveedor


class DetalleCompraForm(forms.ModelForm):
    class Meta:
        model = DetalleCompra
        fields = ["producto", "cantidad", "precio_unitario"]
        widgets = {
            "cantidad": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "precio_unitario": forms.TextInput(attrs={
                "class": "form-control text-end js-cop",
                "inputmode": "numeric",
                "autocomplete": "off",
                "placeholder": "0",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        qs = Producto.objects.filter(activo=True)

        if self.instance and self.instance.producto_id:
            qs = (qs | Producto.objects.filter(pk=self.instance.producto_id)).distinct()

        self.fields["producto"].queryset = qs.order_by("nombre")
        self.fields["producto"].widget.attrs.update({"class": "form-select"})

        self.fields["producto"].label_from_instance = lambda obj: (
            f"{obj.nombre} (Inactivo)" if not obj.activo else obj.nombre
        )

        if self.instance and self.instance.producto_id and not self.instance.producto.activo:
            self.fields["producto"].disabled = True
            self.fields["producto"].help_text = (
                "Este producto está inactivo y no se puede cambiar en una compra existente."
            )

    def clean_producto(self):
        producto = self.cleaned_data.get("producto")

        if self.instance and self.instance.producto_id and not self.instance.producto.activo:
            return self.instance.producto

        if not producto:
            raise forms.ValidationError("Selecciona un producto.")

        if not producto.activo:
            raise forms.ValidationError(
                "Solo puedes registrar compras con productos activos."
            )

        return producto

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get("cantidad")

        if cantidad is None:
            raise forms.ValidationError("La cantidad es obligatoria.")

        if cantidad <= 0:
            raise forms.ValidationError("La cantidad debe ser mayor que 0.")

        if cantidad > MAX_CANTIDAD_COMPRA:
            raise forms.ValidationError(
                f"La cantidad no puede superar {MAX_CANTIDAD_COMPRA} unidades."
            )

        return cantidad

    def clean_precio_unitario(self):
        precio_unitario = self.cleaned_data.get("precio_unitario")

        if precio_unitario is None:
            raise forms.ValidationError("El precio unitario es obligatorio.")

        if precio_unitario <= 0:
            raise forms.ValidationError(
                "El precio unitario debe ser mayor que 0."
            )

        return precio_unitario


class BaseDetalleCompraFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        if any(self.errors):
            return

        hay_detalle = False
        productos_repetidos = {}

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue

            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue

            producto = form.cleaned_data.get("producto")
            cantidad = form.cleaned_data.get("cantidad")
            precio_unitario = form.cleaned_data.get("precio_unitario")

            fila_vacia = not producto and not cantidad and not precio_unitario
            if fila_vacia:
                continue

            if not producto:
                form.add_error("producto", "Selecciona un producto.")
                continue

            if cantidad is None or cantidad <= 0:
                form.add_error("cantidad", "La cantidad debe ser mayor que 0.")
                continue

            if precio_unitario is None or precio_unitario <= 0:
                form.add_error("precio_unitario", "El precio unitario debe ser mayor que 0.")
                continue

            hay_detalle = True
            productos_repetidos.setdefault(producto.pk, []).append(form)

        if not hay_detalle:
            raise forms.ValidationError("Debes agregar al menos un producto a la compra.")

        for _, formularios in productos_repetidos.items():
            if len(formularios) > 1:
                for formulario in formularios:
                    formulario.add_error(
                        "producto",
                        "No puedes repetir el mismo producto en la compra."
                    )


DetalleCompraFormSet = inlineformset_factory(
    Compra,
    DetalleCompra,
    form=DetalleCompraForm,
    formset=BaseDetalleCompraFormSet,
    extra=1,
    can_delete=True,
    validate_min=False
)


class DevolucionCompraForm(forms.ModelForm):
    MOTIVO_CHOICES = [
        ("defecto_fabrica", "Defecto de fábrica"),
        ("producto_incorrecto", "Producto incorrecto"),
        ("producto_danado", "Producto dañado"),
        ("garantia", "Garantía"),
        ("otro", "Otro"),
    ]

    motivo = forms.ChoiceField(
        choices=[("", "Seleccione un motivo")] + MOTIVO_CHOICES,
        required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = DevolucionCompra
        fields = ["compra", "motivo", "observacion"]
        widgets = {
            "compra": forms.Select(attrs={"class": "form-select"}),
            "observacion": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "maxlength": 500,
                "autocomplete": "off",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["compra"].queryset = (
            Compra.objects
            .filter(anulada=False)
            .select_related("proveedor")
            .order_by("-id")
        )
        self.fields["compra"].label_from_instance = lambda obj: (
            f"Compra #{obj.id} - {obj.proveedor.nombre_proveedor}"
        )

    def clean_compra(self):
        compra = self.cleaned_data.get("compra")
        if compra and compra.anulada:
            raise forms.ValidationError("No puedes devolver sobre una compra anulada.")
        return compra

    def clean_motivo(self):
        motivo = (self.cleaned_data.get("motivo") or "").strip()

        validos = {valor for valor, _ in self.MOTIVO_CHOICES}
        if not motivo:
            raise forms.ValidationError("Selecciona un motivo.")

        if motivo not in validos:
            raise forms.ValidationError("Selecciona un motivo válido.")

        return motivo

    def clean_observacion(self):
        observacion = validar_texto_seguro(
            self.cleaned_data.get("observacion"),
            "observación"
        )

        if len(observacion) > 500:
            raise forms.ValidationError(
                "La observación no puede superar 500 caracteres."
            )

        return observacion


class DetalleDevolucionCompraForm(forms.ModelForm):
    class Meta:
        model = DetalleDevolucionCompra
        fields = ["detalle_compra", "cantidad"]
        widgets = {
            "detalle_compra": forms.Select(attrs={"class": "form-select"}),
            "cantidad": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
        }

    def __init__(self, *args, **kwargs):
        self.compra_ref = kwargs.pop("compra", None)
        super().__init__(*args, **kwargs)

        qs = DetalleCompra.objects.none()

        if self.compra_ref is not None:
            qs = (
                DetalleCompra.objects
                .filter(compra=self.compra_ref)
                .select_related("compra", "producto", "compra__proveedor")
                .order_by("producto__nombre")
            )

        self.fields["detalle_compra"].queryset = qs
        self.fields["detalle_compra"].label_from_instance = lambda obj: (
            f"{obj.producto.nombre} - Comprado: {obj.cantidad} - Precio: ${obj.precio_unitario}"
        )

    def clean(self):
        cleaned_data = super().clean()

        detalle_compra = cleaned_data.get("detalle_compra")
        cantidad = cleaned_data.get("cantidad")

        fila_vacia = not detalle_compra and not cantidad
        if fila_vacia:
            return cleaned_data

        if not detalle_compra:
            self.add_error("detalle_compra", "Selecciona un detalle de compra.")
            return cleaned_data

        if not cantidad or cantidad <= 0:
            self.add_error("cantidad", "La cantidad debe ser mayor que 0.")
            return cleaned_data

        if self.compra_ref and detalle_compra.compra_id != self.compra_ref.id:
            self.add_error(
                "detalle_compra",
                "Ese detalle no pertenece a la compra seleccionada."
            )
            return cleaned_data

        qs_devueltas = DetalleDevolucionCompra.objects.filter(
            detalle_compra=detalle_compra,
            devolucion__anulada=False
        )

        if self.instance.pk:
            qs_devueltas = qs_devueltas.exclude(pk=self.instance.pk)

        cantidad_ya_devuelta = qs_devueltas.aggregate(total=Sum("cantidad"))["total"] or 0
        disponible_por_compra = max(
            (detalle_compra.cantidad or 0) - cantidad_ya_devuelta,
            0
        )
        disponible_para_devolver = disponible_por_compra

        if cantidad > disponible_para_devolver:
            self.add_error(
                "cantidad",
                f"Solo puedes devolver hasta {disponible_para_devolver} unidad(es) de este producto."
            )

        return cleaned_data


class BaseDetalleDevolucionCompraFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        if any(self.errors):
            return

        hay_detalle = False
        vistos_por_detalle = {}

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue

            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue

            detalle_compra = form.cleaned_data.get("detalle_compra")
            cantidad = form.cleaned_data.get("cantidad") or 0

            if not detalle_compra and not cantidad:
                continue

            if not detalle_compra:
                form.add_error("detalle_compra", "Selecciona un detalle de compra.")
                continue

            if cantidad <= 0:
                form.add_error("cantidad", "La cantidad debe ser mayor que 0.")
                continue

            if detalle_compra.pk in vistos_por_detalle:
                form.add_error(
                    "detalle_compra",
                    "No puedes repetir el mismo detalle de compra en la misma devolucion.",
                )
                vistos_por_detalle[detalle_compra.pk].add_error(
                    "detalle_compra",
                    "No puedes repetir el mismo detalle de compra en la misma devolucion.",
                )
                continue

            hay_detalle = True
            vistos_por_detalle[detalle_compra.pk] = form

        if not hay_detalle:
            raise forms.ValidationError("Debes agregar al menos un producto a devolver.")

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue

            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue

            detalle_compra = form.cleaned_data.get("detalle_compra")
            if not detalle_compra:
                continue

            qs_devueltas = DetalleDevolucionCompra.objects.filter(
                detalle_compra=detalle_compra,
                devolucion__anulada=False
            )

            if form.instance.pk:
                qs_devueltas = qs_devueltas.exclude(pk=form.instance.pk)

            cantidad_ya_devuelta = qs_devueltas.aggregate(total=Sum("cantidad"))["total"] or 0
            disponible_por_compra = max(
                (detalle_compra.cantidad or 0) - cantidad_ya_devuelta,
                0
            )
            disponible_para_devolver = disponible_por_compra

            if cantidad > disponible_para_devolver:
                form.add_error(
                    "cantidad",
                    f"Solo puedes devolver hasta {disponible_para_devolver} unidad(es) de este producto."
                )


DetalleDevolucionCompraFormSet = inlineformset_factory(
    DevolucionCompra,
    DetalleDevolucionCompra,
    form=DetalleDevolucionCompraForm,
    formset=BaseDetalleDevolucionCompraFormSet,
    extra=1,
    can_delete=True,
    validate_min=False
)
