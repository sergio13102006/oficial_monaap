import os
from datetime import datetime

from backup.constants import BACKUP_ACTION_IMPORTED, BACKUP_STATUS_SUCCESS
from backup.models import BackupRecord

from .storage_service import calculate_checksum, delete_backup_file, get_backup_file_size, save_backup_file
from .validation_service import sanitize_backup_name, validate_backup_zip


def import_backup(uploaded_file, usuario=None, notas=""):
    validacion = validate_backup_zip(uploaded_file)
    temp_path = validacion["temp_path"]
    meta = validacion["meta"]
    tipo = validacion["tipo"]
    nombre_original = validacion["nombre_original"]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    nombre_base = sanitize_backup_name(
        str(meta.get("nombre_visible") or os.path.splitext(os.path.basename(nombre_original))[0]),
        f"backup_importado_{timestamp}",
    )
    try:
        archivo_final = save_backup_file(temp_path, nombre_base)
        return BackupRecord.objects.create(
            nombre=nombre_base,
            tipo=tipo,
            estado=BACKUP_STATUS_SUCCESS,
            archivo=archivo_final,
            tamano=get_backup_file_size(archivo_final),
            checksum=calculate_checksum(archivo_final),
            usuario=usuario,
            notas=notas.strip() or f"Importado desde {nombre_original}",
            tablas_incluidas="Importado",
            duracion_segundos=0,
            ultima_accion=BACKUP_ACTION_IMPORTED,
            db_engine=meta.get("db_engine") or "sqlite",
            incluye_media=bool(meta.get("includes_media")),
            origen=meta.get("source_environment") or "importado",
            es_backup_seguridad=bool(meta.get("is_security_backup")),
        )
    finally:
        delete_backup_file(temp_path)
