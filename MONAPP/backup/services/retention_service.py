from backup.constants import BACKUP_STATUS_SUCCESS
from backup.models import BackupRecord

from .config_service import get_retention_limit, get_security_retention_limit
from .storage_service import delete_backup_file, path_exists


def should_keep_backup(record, keep_ids):
    return record.pk in keep_ids


def get_backups_exceeding_limit(limit=None):
    limit = int(limit or get_retention_limit())
    valid_backups = BackupRecord.objects.exclude(estado="en_progreso").order_by(
        "-fecha_creacion"
    )
    keep = list(valid_backups[:limit].values_list("id", flat=True))
    return valid_backups.exclude(id__in=keep), set(keep)


def delete_old_backup(record):
    if path_exists(record.archivo):
        delete_backup_file(record.archivo)
    nombre = record.nombre
    record.delete()
    return nombre


def apply_retention_policy(limit=None):
    queryset, keep_ids = get_backups_exceeding_limit(limit=limit)
    eliminados = []
    errores = []
    security_limit = get_security_retention_limit()
    last_success = (
        BackupRecord.objects.filter(estado=BACKUP_STATUS_SUCCESS)
        .order_by("-fecha_creacion")
        .first()
    )
    keep_security_ids = set(
        BackupRecord.objects.filter(es_backup_seguridad=True)
        .order_by("-fecha_creacion")
        .values_list("id", flat=True)[:security_limit]
    )
    for record in queryset:
        if last_success and record.pk == last_success.pk:
            continue
        if record.es_backup_seguridad and record.pk in keep_security_ids:
            continue
        if should_keep_backup(record, keep_ids):
            continue
        try:
            eliminados.append(delete_old_backup(record))
        except Exception as exc:
            errores.append({"id": record.pk, "error": str(exc)})
    return {
        "eliminados": len(eliminados),
        "nombres": eliminados,
        "errores": errores,
        "limite": limit or get_retention_limit(),
    }
