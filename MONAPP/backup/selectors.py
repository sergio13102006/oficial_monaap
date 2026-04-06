import os
from datetime import date

from django.core.paginator import Paginator
from django.db.models import Q
from django.conf import settings
from django.db import connection

from .models import BackupConfig, BackupRecord


SORT_MAP = {
    "nombre": ("nombre",),
    "tipo": ("tipo", "nombre"),
    "estado": ("estado", "nombre"),
    "tamano": ("tamano", "nombre"),
    "fecha": ("fecha_creacion",),
}


def normalize_choice(value, allowed_map):
    value = (value or "").strip()
    return value if value in allowed_map else ""


def get_backup_dir():
    config = BackupConfig.get_config()
    backup_dir = config.ruta_backups or os.path.join(settings.BASE_DIR, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir


def build_backup_dashboard_queryset(filters):
    query = (filters.get("q") or "").strip()
    estado = normalize_choice(filters.get("estado"), dict(BackupRecord.ESTADO_CHOICES))
    tipo = normalize_choice(filters.get("tipo"), dict(BackupRecord.TIPO_CHOICES))
    fecha_desde_raw = (filters.get("fecha_desde") or "").strip()
    fecha_hasta_raw = (filters.get("fecha_hasta") or "").strip()
    current_sort = (filters.get("sort") or "fecha").strip()
    current_dir = (filters.get("dir") or "desc").strip().lower()
    if current_dir not in {"asc", "desc"}:
        current_dir = "desc"

    qs = BackupRecord.objects.exclude(estado="en_progreso")
    if query:
        qs = qs.filter(
            Q(nombre__icontains=query)
            | Q(notas__icontains=query)
            | Q(tipo__icontains=query)
            | Q(estado__icontains=query)
            | Q(usuario__username__icontains=query)
        )
    if estado:
        qs = qs.filter(estado=estado)
    if tipo:
        qs = qs.filter(tipo=tipo)

    try:
        if fecha_desde_raw:
            qs = qs.filter(fecha_creacion__date__gte=date.fromisoformat(fecha_desde_raw))
    except ValueError:
        fecha_desde_raw = ""
    try:
        if fecha_hasta_raw:
            qs = qs.filter(fecha_creacion__date__lte=date.fromisoformat(fecha_hasta_raw))
    except ValueError:
        fecha_hasta_raw = ""

    if current_sort not in SORT_MAP:
        current_sort = "fecha"
        current_dir = "desc"

    order_fields = []
    for field in SORT_MAP[current_sort]:
        order_fields.append(field if current_dir == "asc" else f"-{field}")
    qs = qs.order_by(*order_fields)

    return {
        "queryset": qs,
        "query": query,
        "estado": estado or "",
        "tipo": tipo or "",
        "fecha_desde": fecha_desde_raw,
        "fecha_hasta": fecha_hasta_raw,
        "current_sort": current_sort,
        "current_dir": current_dir,
    }


def get_dashboard_page(filters, per_page=20):
    data = build_backup_dashboard_queryset(filters)
    paginator = Paginator(data["queryset"], per_page)
    page_obj = paginator.get_page(filters.get("page"))
    data["page_obj"] = page_obj
    data["backups"] = page_obj.object_list
    return data


def get_backup_dashboard_summary(filtered_queryset):
    return {
        "config": BackupConfig.get_config(),
        "total_backups": BackupRecord.objects.exclude(estado="en_progreso").count(),
        "exitosos": BackupRecord.objects.filter(estado="exitoso").count(),
        "fallidos": BackupRecord.objects.filter(estado="fallido").count(),
        "ultimo_backup": BackupRecord.objects.filter(estado="exitoso")
        .order_by("-fecha_creacion")
        .first(),
        "historial_total": filtered_queryset.count(),
    }


def get_database_path():
    return settings.DATABASES["default"]["NAME"]


def get_all_tables():
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
        )
        return [row[0] for row in cursor.fetchall()]


def get_table_info():
    tables = get_all_tables()
    info = []
    with connection.cursor() as cursor:
        for table in tables:
            try:
                cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
                count = cursor.fetchone()[0]
            except Exception:
                count = 0
            info.append({"nombre": table, "registros": count})
    return info


def _format_size(size_bytes):
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def get_database_stats():
    db_path = str(get_database_path())
    db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
    tables = get_table_info()
    total_registros = sum(t["registros"] for t in tables)

    media_root = getattr(settings, "MEDIA_ROOT", "")
    media_size = 0
    media_files = 0
    if media_root and os.path.exists(str(media_root)):
        for dirpath, _, filenames in os.walk(str(media_root)):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                media_size += os.path.getsize(filepath)
                media_files += 1

    return {
        "db_size": db_size,
        "db_size_legible": _format_size(db_size),
        "total_tablas": len(tables),
        "total_registros": total_registros,
        "tablas": tables,
        "media_size": media_size,
        "media_size_legible": _format_size(media_size),
        "media_files": media_files,
        "backup_dir": get_backup_dir(),
    }
