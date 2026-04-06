from backup.constants import (
    BACKUP_STATUS_FAILED,
    BACKUP_STATUS_IN_PROGRESS,
    BACKUP_STATUS_RESTORED,
    BACKUP_STATUS_SUCCESS,
)
from backup.models import BackupRecord


def create_backup_record(*, nombre, tipo, usuario=None, notas="", estado=None):
    return BackupRecord.objects.create(
        nombre=nombre,
        tipo=tipo,
        estado=estado or BACKUP_STATUS_IN_PROGRESS,
        usuario=usuario,
        notas=notas or "",
    )


def mark_backup_success(record, *, archivo, tamano, duracion_segundos, tablas_incluidas=""):
    record.archivo = archivo
    record.tamano = tamano
    record.estado = BACKUP_STATUS_SUCCESS
    record.duracion_segundos = round(duracion_segundos, 2)
    record.tablas_incluidas = tablas_incluidas or ""
    record.save()
    return record


def mark_backup_failed(record, error, *, notas="", duracion_segundos=0):
    record.estado = BACKUP_STATUS_FAILED
    record.notas = f"{notas}\nError: {error}" if notas else f"Error: {error}"
    record.duracion_segundos = round(duracion_segundos, 2)
    record.save()
    return record


def mark_backup_restored(record):
    record.estado = BACKUP_STATUS_RESTORED
    record.save()
    return record


def snapshot_current_backup_history():
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
    )
    return [
        dict(row)
        for row in BackupRecord.objects.exclude(estado=BACKUP_STATUS_IN_PROGRESS).values(*fields)
    ]
