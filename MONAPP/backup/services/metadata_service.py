import json
from datetime import datetime

from backup.constants import BACKUP_FORMAT_VERSION, BACKUP_META_FILENAME
from backup.exceptions import BackupValidationError


def build_backup_metadata(
    *,
    nombre,
    tipo,
    usuario=None,
    notas="",
    tablas=None,
    extra=None,
):
    payload = {
        "version": BACKUP_FORMAT_VERSION,
        "nombre": nombre,
        "tipo": tipo,
        "fecha": datetime.now().isoformat(),
        "usuario": str(usuario) if usuario else "Sistema",
        "notas": notas or "",
        "tablas": tablas or [],
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
    version = meta.get("version", 1)
    if int(version) < 1:
        raise BackupValidationError("La versión del backup no es válida.")
    return int(version)


def read_metadata_from_zip(zip_file):
    if BACKUP_META_FILENAME not in zip_file.namelist():
        raise BackupValidationError("El ZIP debe incluir el archivo backup_meta.json.")
    meta = deserialize_backup_metadata(zip_file.read(BACKUP_META_FILENAME))
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
                if normalizado.endswith("db.sqlite3"):
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
            }
    except Exception:
        return None

