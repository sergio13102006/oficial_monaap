import os
import re
import zipfile

from backup.constants import (
    BACKUP_DB_FILENAME,
    BACKUP_META_FILENAME,
    BACKUP_TYPES,
    DB_ENGINES,
    RESTORE_MODES,
)
from backup.exceptions import BackupValidationError

from .metadata_service import read_metadata_from_zip
from .storage_service import calculate_zip_content_checksum, delete_backup_file, save_uploaded_file


def normalize_choice(value, allowed_map):
    value = (value or "").strip()
    return value if value in allowed_map else ""


def normalize_zip_member(name):
    if not name:
        return None
    if name.endswith("/"):
        return None
    normalized = os.path.normpath(name).replace("\\", "/")
    if os.path.isabs(name) or normalized.startswith("../") or "/.." in normalized:
        raise BackupValidationError("El ZIP contiene rutas no permitidas.")
    return normalized


def is_safe_zip_member(name):
    try:
        return normalize_zip_member(name) is not None
    except BackupValidationError:
        return False


def media_relative_path(normalized_name):
    if not normalized_name:
        return None
    parts = normalized_name.split("/")
    if "media" not in parts:
        return None
    idx = parts.index("media")
    if idx == len(parts) - 1:
        return None
    return "/".join(parts[idx + 1 :])


def sanitize_backup_name(raw_name, default_prefix):
    safe_name = re.sub(r"[^A-Za-z0-9_\-\.\s]+", "_", (raw_name or "").strip()).strip()
    return safe_name or default_prefix


def validate_backup_metadata(meta):
    tipo = str(meta.get("backup_type") or meta.get("tipo") or "").strip().lower()
    if tipo not in BACKUP_TYPES:
        raise BackupValidationError("El backup no indica un tipo vÃ¡lido.")
    engine = str(meta.get("db_engine") or "").strip().lower()
    if engine and engine not in DB_ENGINES:
        raise BackupValidationError("El backup declara un motor de base de datos no soportado.")
    supported_modes = meta.get("restore_mode_supported") or []
    if supported_modes and not all(mode in RESTORE_MODES for mode in supported_modes):
        raise BackupValidationError("El backup declara modos de restore no soportados.")
    return tipo


def validate_backup_structure(zip_file, meta):
    names = zip_file.namelist()
    safe_names = []
    db_members = []
    media_members = []

    for name in names:
        normalized = normalize_zip_member(name)
        if not normalized:
            continue
        safe_names.append(normalized)
        base_name = os.path.basename(normalized).lower()
        if base_name in {BACKUP_DB_FILENAME.lower(), "db.dump", "db.sql"}:
            db_members.append(normalized)
        if media_relative_path(normalized) is not None:
            media_members.append(normalized)

    if BACKUP_META_FILENAME not in safe_names:
        raise BackupValidationError("El ZIP debe incluir el archivo backup_meta.json.")

    tipo = validate_backup_metadata(meta)
    includes_media = bool(meta.get("includes_media"))

    if tipo in {"completo", "base_datos"} and not db_members:
        raise BackupValidationError("El ZIP no contiene el payload de base de datos esperado.")
    if tipo == "media" and not media_members:
        raise BackupValidationError("El ZIP no contiene archivos de media.")
    if includes_media and not media_members:
        raise BackupValidationError("El metadata indica media, pero el ZIP no la contiene.")
    if not includes_media and media_members and tipo != "media":
        raise BackupValidationError("El ZIP contiene media no declarada en el metadata.")

    return {
        "safe_names": safe_names,
        "db_members": db_members,
        "media_members": media_members,
        "tipo": tipo,
    }


def validate_engine_compatibility(meta, current_engine_name, allow_cross_engine=False):
    source_engine = (meta or {}).get("db_engine") or "sqlite"
    if source_engine == current_engine_name:
        return True
    raise BackupValidationError(
        "Este respaldo pertenece a otro motor y requiere flujo de migracion/importacion, no restauracion directa."
    )


def validate_archive_checksum(path, meta):
    expected = (meta or {}).get("checksum") or ""
    if not expected:
        return True
    current = calculate_zip_content_checksum(path, skip_members={BACKUP_META_FILENAME})
    if current != expected:
        raise BackupValidationError("El checksum del respaldo no coincide con los metadatos.")
    return True


def validate_restore_mode(mode, *, config):
    mode = (mode or "").strip().lower() or config.restore_mode_default
    if mode not in RESTORE_MODES:
        raise BackupValidationError("El modo de restore no es soportado.")
    if mode == "mirror" and not config.habilitar_mirror_media:
        raise BackupValidationError("El modo mirror de media estÃ¡ deshabilitado en la configuraciÃ³n.")
    return mode


def validate_backup_zip(uploaded_file):
    if not uploaded_file:
        raise BackupValidationError("Debes seleccionar un archivo ZIP.")
    if os.path.splitext(getattr(uploaded_file, "name", "") or "")[1].lower() != ".zip":
        raise BackupValidationError("Solo se permiten archivos .zip.")
    if getattr(uploaded_file, "size", 0) <= 0:
        raise BackupValidationError("El archivo ZIP estÃ¡ vacÃ­o.")

    temp_path = save_uploaded_file(uploaded_file, suffix=".zip")
    try:
        if not zipfile.is_zipfile(temp_path):
            raise BackupValidationError("El archivo no es un ZIP vÃ¡lido.")
        with zipfile.ZipFile(temp_path, "r") as zf:
            meta = read_metadata_from_zip(zf)
            structure = validate_backup_structure(zf, meta)
        validate_archive_checksum(temp_path, meta)
        return {
            "temp_path": temp_path,
            "meta": meta,
            "tipo": structure["tipo"],
            "nombre_original": getattr(uploaded_file, "name", "") or "",
        }
    except Exception:
        delete_backup_file(temp_path)
        raise
