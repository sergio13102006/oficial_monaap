from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, key)


@register.filter
def index(sequence, i):
    """Retorna el elemento en la posición i, o None si no existe."""
    try:
        return sequence[int(i)]
    except (IndexError, TypeError, ValueError):
        return None


@register.filter
def subtract(value, arg):
    """Resta arg de value. Funciona con int, float y Decimal."""
    try:
        return float(value) - float(arg)
    except (TypeError, ValueError):
        return None


@register.filter
def abs_value(value):
    """Valor absoluto."""
    try:
        return abs(value)
    except (TypeError, ValueError):
        return value