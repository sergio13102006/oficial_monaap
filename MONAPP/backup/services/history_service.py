from django.utils import timezone

from backup.constants import (
    BACKUP_ACTION_CREATED,
    BACKUP_ACTION_FAILED,
    BACKUP_ACTION_FAILED_CREATE,
    BACKUP_ACTION_FAILED_IMPORT,
    BACKUP_ACTION_FAILED_RESTORE,
    BACKUP_ACTION_IMPORTED,
    BACKUP_ACTION_RESTORED,
    BACKUP_ACTION_SECURITY,
    BACKUP_STATUS_FAILED,
    BACKUP_STATUS_IN_PROGRESS,
    BACKUP_STATUS_SUCCESS,
)
from backup.models import BackupRecord


def create_event_record(
    *,
    nombre,
    tipo,
    usuario=None,
    notas="",
    estado=None,
    accion=BACKUP_ACTION_CREATED,
    db_engine="sqlite",
    incluye_media=False,
    origen="local",
    es_backup_seguridad=False,
    backup_padre=None,
):
    return BackupRecord.objects.create(
        nombre=nombre,
        tipo=tipo,
        estado=estado or BACKUP_STATUS_IN_PROGRESS,
        usuario=usuario,
        notas=notas or "",
        ultima_accion=accion,
        db_engine=db_engine,
        incluye_media=incluye_media,
        origen=origen,
        es_backup_seguridad=es_backup_seguridad,
        backup_padre=backup_padre,
    )


def create_backup_record(*, nombre, tipo, usuario=None, notas="", estado=None, **kwargs):
    return create_event_record(
        nombre=nombre,
        tipo=tipo,
        usuario=usuario,
        notas=notas,
        estado=estado,
        **kwargs,
    )


def mark_success(record, *, archivo, tamano, checksum="", duracion_segundos=0, tablas_incluidas=""):
    record.archivo = archivo
    record.tamano = tamano
    record.estado = BACKUP_STATUS_SUCCESS
    record.checksum = checksum or ""
    record.duracion_segundos = round(duracion_segundos, 2)
    record.tablas_incluidas = tablas_incluidas or ""
    if record.ultima_accion == BACKUP_ACTION_FAILED:
        record.ultima_accion = BACKUP_ACTION_CREATED
    record.save()
    return record


def mark_backup_success(record, *, archivo, tamano, checksum="", duracion_segundos=0, tablas_incluidas=""):
    return mark_success(
        record,
        archivo=archivo,
        tamano=tamano,
        checksum=checksum,
        duracion_segundos=duracion_segundos,
        tablas_incluidas=tablas_incluidas,
    )


def mark_failed(record, error, *, notas="", duracion_segundos=0, action=BACKUP_ACTION_FAILED):
    record.estado = BACKUP_STATUS_FAILED
    record.ultima_accion = action
    record.notas = f"{notas}\nError: {error}" if notas else f"Error: {error}"
    record.detalle_error = str(error)
    record.duracion_segundos = round(duracion_segundos, 2)
    record.save()
    return record


def mark_backup_failed(record, error, *, notas="", duracion_segundos=0, action=BACKUP_ACTION_FAILED_CREATE):
    return mark_failed(record, error, notas=notas, duracion_segundos=duracion_segundos, action=action)


def mark_restored(record):
    record.ultima_accion = BACKUP_ACTION_RESTORED
    record.veces_restaurado = (record.veces_restaurado or 0) + 1
    record.fecha_ultima_restauracion = timezone.now()
    if record.estado == BACKUP_STATUS_IN_PROGRESS:
        record.estado = BACKUP_STATUS_SUCCESS
    record.save(update_fields=["ultima_accion", "veces_restaurado", "fecha_ultima_restauracion", "estado"])
    return record


def mark_backup_restored(record):
    return mark_restored(record)


def snapshot_current_history():
    fields = (
        "nombre",
        "tipo",
        "estado",
        "archivo",
        "tamano",
        "fecha_creacion",
        "usuario_id",
        "notas",
        "es_automatico",
        "tablas_incluidas",
        "duracion_segundos",
        "ultima_accion",
        "veces_restaurado",
        "fecha_ultima_restauracion",
        "checksum",
        "db_engine",
        "incluye_media",
        "origen",
        "es_backup_seguridad",
        "backup_padre_id",
        "detalle_error",
    )
    return [
        dict(row)
        for row in BackupRecord.objects.exclude(estado=BACKUP_STATUS_IN_PROGRESS).values(*fields)
    ]


def snapshot_current_backup_history():
    return snapshot_current_history()
