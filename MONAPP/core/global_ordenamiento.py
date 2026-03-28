from django.core.exceptions import FieldDoesNotExist

FK_PREFERRED_FIELDS = ("nombre", "name", "username", "email", "titulo", "title", "razon_social")


def _is_valid_field(model, field_name: str) -> bool:
    """Valida si field_name es un campo real del modelo."""
    try:
        model._meta.get_field(field_name)
        return True
    except FieldDoesNotExist:
        return False


def _resolve_fk_ordering(model, field_name: str) -> str | None:
    """
    Si field_name es un ForeignKey/OneToOne, intenta devolver:
      'field__nombre' o 'field__name' o 'field__username' ...
    Si no puede, retorna None.
    """
    try:
        f = model._meta.get_field(field_name)
    except FieldDoesNotExist:
        return None

    if not getattr(f, "is_relation", False) or getattr(f, "many_to_many", False):
        return None

    rel_model = getattr(f, "related_model", None)
    if not rel_model:
        return None

    for cand in FK_PREFERRED_FIELDS:
        try:
            rel_model._meta.get_field(cand)
            return f"{field_name}__{cand}"
        except FieldDoesNotExist:
            continue

    return None


def _build_allowed_sort_map(model, aliases=None) -> dict:
    """
    Crea un mapa seguro:
      sort_key (lo que llega en ?sort=) -> campo DB para order_by()
    """
    aliases = aliases or {}
    allowed = {}

    for k, v in aliases.items():
        allowed[k] = v

    for f in model._meta.get_fields():
        if getattr(f, "auto_created", False):
            continue
        if getattr(f, "many_to_many", False):
            continue

        name = getattr(f, "name", None)
        if not name:
            continue

        if name in allowed:
            continue

        if getattr(f, "is_relation", False):
            fk_order = _resolve_fk_ordering(model, name)
            allowed[name] = fk_order or name  
        else:
            allowed[name] = name

    return allowed


def apply_smart_sorting(
    request,
    qs,
    default_sort="id",
    default_dir="desc",
    aliases=None,
):
    """
    Aplica ordenamiento a un QuerySet basado en:
      ?sort=campo&dir=asc|desc

    - Seguro: solo permite campos reales o aliases definidos.
    - FK: intenta ordenar por nombre/name/username... del relacionado.
    - No rompe si piden un campo inexistente: cae al default_sort.

    Retorna: (qs_ordenado, sort_key, direction)
    """
    model = qs.model
    allowed = _build_allowed_sort_map(model, aliases=aliases)

    sort_key = (request.GET.get("sort") or default_sort).strip()
    direction = (request.GET.get("dir") or default_dir).lower().strip()
    direction = "desc" if direction == "desc" else "asc"

    if sort_key not in allowed:
        if default_sort in allowed:
            sort_key = default_sort
        else:
            sort_key = next(iter(allowed.keys()), "id")

    sort_db = allowed.get(sort_key, default_sort)

    if direction == "desc":
        qs = qs.order_by(f"-{sort_db}")
    else:
        qs = qs.order_by(sort_db)

    return qs, sort_key, direction


def sorting_context(sort_key: str, direction: str) -> dict:
    """
    Helper opcional para pasar al template y saber
    qué columna/dirección están activas.
    """
    return {
        "current_sort": sort_key,
        "current_dir": direction,
    }