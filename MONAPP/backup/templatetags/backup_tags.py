from django import template

register = template.Library()


@register.filter
def split_comma(value):
    """Divide un string por ', ' y devuelve una lista."""
    if not value:
        return []
    return [v.strip() for v in value.split(',') if v.strip()]
