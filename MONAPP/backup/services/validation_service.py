import os
import re
import zipfile

from backup.constants import BACKUP_DB_FILENAME, BACKUP_META_FILENAME, BACKUP_TYPES
from backup.exceptions import BackupValidationError
from .metadata_service import read_metadata_from_zip
from .storage_service import delete_backup_file, save_uploaded_file


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


def validate_backup_metadata(meta):
    tipo = str(meta.get("tipo", "")).strip().lower()
    if tipo not in BACKUP_TYPES:
        raise BackupValidationError("El backup no indica un tipo válido.")
    tablas = meta.get("tablas")
    if tablas is not None and not isinstance(tablas, (list, tuple, str)):
        raise BackupValidationError("El metadato de tablas no es válido.")
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
        if os.path.basename(normalized).lower() == BACKUP_DB_FILENAME.lower():
            db_members.append(normalized)
        if media_relative_path(normalized) is not None:
            media_members.append(normalized)

    if BACKUP_META_FILENAME not in safe_names:
        raise BackupValidationError("El ZIP debe incluir el archivo backup_meta.json.")

    tipo = validate_backup_metadata(meta)
    if tipo in {"completo", "base_datos"} and not db_members:
        raise BackupValidationError("El ZIP no contiene la base de datos db.sqlite3.")
    if tipo == "media" and not media_members:
        raise BackupValidationError("El ZIP no contiene archivos de media.")

    return {
        "safe_names": safe_names,
        "db_members": db_members,
        "media_members": media_members,
        "tipo": tipo,
    }


def validate_backup_zip(uploaded_file):
    if not uploaded_file:
        raise BackupValidationError("Debes seleccionar un archivo ZIP.")
    if os.path.splitext(getattr(uploaded_file, "name", "") or "")[1].lower() != ".zip":
        raise BackupValidationError("Solo se permiten archivos .zip.")
    if getattr(uploaded_file, "size", 0) <= 0:
        raise BackupValidationError("El archivo ZIP está vacío.")

    temp_path = save_uploaded_file(uploaded_file, suffix=".zip")
    try:
        if not zipfile.is_zipfile(temp_path):
            raise BackupValidationError("El archivo no es un ZIP válido.")
        with zipfile.ZipFile(temp_path, "r") as zf:
            meta = read_metadata_from_zip(zf)
            structure = validate_backup_structure(zf, meta)
        return {
            "temp_path": temp_path,
            "meta": meta,
            "tipo": structure["tipo"],
            "nombre_original": getattr(uploaded_file, "name", "") or "",
        }
    except Exception:
        delete_backup_file(temp_path)
        raise


def sanitize_backup_name(raw_name, default_prefix):
    safe_name = re.sub(r"[^A-Za-z0-9_\-\.\s]+", "_", (raw_name or "").strip()).strip()
    return safe_name or default_prefix

