import json
from datetime import datetime

from django.conf import settings

from backup.constants import (
    BACKUP_DEFAULT_RESTORE_MODE,
    BACKUP_FORMAT_VERSION,
    BACKUP_META_FILENAME,
    DB_ENGINE_SQLITE,
)
from backup.exceptions import BackupValidationError


def build_backup_metadata(
    *,
    nombre,
    tipo,
    usuario=None,
    notas="",
    db_engine=DB_ENGINE_SQLITE,
    includes_media=False,
    checksum="",
    restore_mode_supported=None,
    is_security_backup=False,
    source_environment="local",
    app_version="dev",
    extra=None,
):
    payload = {
        "format_version": BACKUP_FORMAT_VERSION,
        "backup_type": tipo,
        "nombre_visible": nombre,
        "db_engine": db_engine,
        "app_version": app_version,
        "created_at": datetime.now().isoformat(),
        "includes_media": bool(includes_media),
        "restore_mode_supported": restore_mode_supported or [BACKUP_DEFAULT_RESTORE_MODE],
        "checksum": checksum,
        "created_by": str(usuario) if usuario else "Sistema",
        "is_security_backup": bool(is_security_backup),
        "source_environment": source_environment,
        "notas": notas or "",
    }
    if extra:
        payload.update(extra)
    return payload


def serialize_backup_metadata(meta):
    return json.dumps(meta, indent=2, ensure_ascii=False)


def deserialize_backup_metadata(raw):
    try:
        return json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
    except Exception as exc:
        raise BackupValidationError("No se pudo leer backup_meta.json.") from exc


def validate_metadata_version(meta):
    version = meta.get("format_version") or meta.get("version") or 1
    try:
        version = int(version)
    except (TypeError, ValueError) as exc:
        raise BackupValidationError("La versiÃ³n del backup no es vÃ¡lida.") from exc
    if version < 1:
        raise BackupValidationError("La versiÃ³n del backup no es vÃ¡lida.")
    return version


def read_metadata_from_zip(zip_file):
    if BACKUP_META_FILENAME not in zip_file.namelist():
        raise BackupValidationError("El ZIP debe incluir el archivo backup_meta.json.")
    meta_info = None
    for info in zip_file.infolist():
        if info.filename == BACKUP_META_FILENAME:
            meta_info = info
    if meta_info is None:
        raise BackupValidationError("El ZIP debe incluir el archivo backup_meta.json.")
    meta = deserialize_backup_metadata(zip_file.read(meta_info))
    validate_metadata_version(meta)
    return meta


def read_backup_metadata(filepath):
    from .storage_service import open_backup_zip
    from .validation_service import media_relative_path, normalize_zip_member

    try:
        with open_backup_zip(filepath, "r") as zf:
            nombres = zf.namelist()
            meta = None
            archivos = []
            db_member = None
            media_members = []

            for nombre in nombres:
                normalizado = normalize_zip_member(nombre)
                if not normalizado:
                    continue
                if normalizado == BACKUP_META_FILENAME:
                    meta = deserialize_backup_metadata(zf.read(nombre))
                    continue
                archivos.append(normalizado)
                if normalizado.endswith(".sqlite3") or normalizado.endswith(".dump") or normalizado.endswith(".sql"):
                    db_member = normalizado
                if media_relative_path(normalizado) is not None:
                    media_members.append(normalizado)

            return {
                "meta": meta,
                "archivos": archivos,
                "db_archivo": db_member,
                "media_archivos": media_members,
                "total_archivos": len(archivos),
                "tiene_db": bool(db_member),
                "tiene_media": bool(media_members),
                "engine": (meta or {}).get("db_engine"),
                "source_environment": (meta or {}).get("source_environment") or getattr(settings, "ENVIRONMENT", "local"),
            }
    except Exception:
        return None
