from django import forms
from django.utils.encoding import force_str


NUMERIC_KEYWORDS = (
    "documento",
    "cedula",
    "nit",
    "telefono",
    "celular",
    "cantidad",
    "stock",
    "edad",
    "codigo",
    "numero",
)

DECIMAL_KEYWORDS = (
    "precio",
    "total",
    "saldo",
    "anticipo",
    "descuento",
    "porcentaje",
    "valor",
    "monto",
    "costo",
)

ALPHA_KEYWORDS = (
    "nombre",
    "nombres",
    "apellido",
    "apellidos",
    "marca",
    "linea",
    "rol",
    "ciudad",
)

ALNUM_KEYWORDS = (
    "descripcion",
    "direccion",
    "observacion",
    "motivo",
    "detalle",
    "presentacion",
    "placa",
    "usuario",
    "referencia",
    "producto",
    "servicio",
    "procedimiento",
    "recomendacion",
    "medicamento",
    "frecuencia",
)

SKIP_KEYWORDS = (
    "email",
    "correo",
    "password",
    "contrasena",
    "contraseña",
    "url",
    "imagen",
    "video",
    "archivo",
    "foto",
    "search",
    "busqueda",
)


def _signature(field_name, field):
    parts = [
        force_str(field_name or ""),
        force_str(getattr(field, "label", "") or ""),
        force_str(field.widget.attrs.get("placeholder", "") or ""),
    ]
    return " ".join(parts).lower()


def _guess_validation_rule(field_name, field):
    widget = field.widget
    signature = _signature(field_name, field)

    if any(keyword in signature for keyword in SKIP_KEYWORDS):
        return None

    if "documento" in signature and ("usuario" in signature or "username" in signature):
        return "alnum"

    if isinstance(widget, (
        forms.CheckboxInput,
        forms.ClearableFileInput,
        forms.FileInput,
        forms.DateInput,
        forms.DateTimeInput,
        forms.TimeInput,
    )):
        return None

    if isinstance(field, (forms.DecimalField, forms.FloatField)):
        return "decimal"

    if isinstance(field, forms.IntegerField):
        return "numeric"

    if isinstance(field, forms.EmailField):
        return None

    if isinstance(widget, forms.NumberInput):
        step = str(widget.attrs.get("step", "")).strip()
        return "decimal" if step and step != "1" else "numeric"

    if any(keyword in signature for keyword in DECIMAL_KEYWORDS):
        return "decimal"

    if any(keyword in signature for keyword in NUMERIC_KEYWORDS):
        return "numeric"

    if "nombre" in signature and any(
        keyword in signature for keyword in ("producto", "servicio", "promocion", "promoción", "web")
    ):
        return "alnum"

    if any(keyword in signature for keyword in ALPHA_KEYWORDS):
        return "alpha"

    if any(keyword in signature for keyword in ALNUM_KEYWORDS):
        return "alnum"

    if isinstance(widget, forms.Textarea):
        return "text"

    if isinstance(widget, forms.TextInput):
        return "text"

    return None


def _apply_validation_attrs(field_name, field):
    attrs = field.widget.attrs
    if attrs.get("data-validate"):
        return

    rule = _guess_validation_rule(field_name, field)
    if not rule:
        return

    attrs["data-validate"] = rule

    if rule == "numeric":
        attrs.setdefault("inputmode", "numeric")
        attrs.setdefault("pattern", "[0-9]*")
        attrs.setdefault("title", "Solo se permiten numeros.")
    elif rule == "decimal":
        attrs.setdefault("inputmode", "decimal")
        attrs.setdefault("title", "Solo se permiten numeros.")
    elif rule == "alpha":
        attrs.setdefault("title", "Solo se permiten letras y espacios.")
    elif rule in {"text", "alnum"}:
        attrs.setdefault("title", "No se permiten simbolos especiales.")


class ValidationFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            _apply_validation_attrs(field_name, field)
