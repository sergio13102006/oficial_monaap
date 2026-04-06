import os

from backup.exceptions import BackupRestoreError

from .backup_service import create_full_backup
from .config_service import get_backup_config
from .engines import get_current_database_engine, get_database_engine, media_engine
from .history_service import mark_failed, mark_restored, snapshot_current_history
from .metadata_service import read_metadata_from_zip
from .storage_service import cleanup_temp_dir, create_temp_dir, open_backup_zip, path_exists, validate_checksum
from .validation_service import (
    media_relative_path,
    normalize_zip_member,
    validate_archive_checksum,
    validate_backup_structure,
    validate_engine_compatibility,
    validate_restore_mode,
)

sqlite_engine = get_database_engine("sqlite")


def restore_backup(record_or_path, user=None, mode=None, create_safety_backup=None):
    record = getattr(record_or_path, "archivo", None) and record_or_path or None
    filepath = record.archivo if record else str(record_or_path)
    if not path_exists(filepath):
        raise FileNotFoundError("El archivo de backup no existe.")

    config = get_backup_config()
    mode = validate_restore_mode(mode, config=config)
    create_safety_backup = config.crear_backup_pre_restore if create_safety_backup is None else create_safety_backup
    if mode == "mirror" and not create_safety_backup:
        raise BackupRestoreError("El modo mirror requiere backup de seguridad previo obligatorio.")
    engine = get_current_database_engine()
    temp_dir = create_temp_dir(prefix="restore_stage_")
    historial_prev = snapshot_current_history()
    safety_record = None

    if create_safety_backup:
        safety_record = create_full_backup(
            nombre=None,
            usuario=user,
            notas="Backup de seguridad previo a restauracion",
            es_backup_seguridad=True,
            backup_padre=record,
        )

    try:
        with open_backup_zip(filepath, "r") as zf:
            try:
                metadata = read_metadata_from_zip(zf)
                structure = validate_backup_structure(zf, metadata)
            except Exception:
                names = [normalize_zip_member(name) for name in zf.namelist() if normalize_zip_member(name)]
                db_members = [name for name in names if name.endswith(".sqlite3") or name.endswith(".sql") or name.endswith(".dump")]
                media_members = [name for name in names if media_relative_path(name) is not None]
                metadata = {
                    "backup_type": "completo" if db_members else "media",
                    "db_engine": "sqlite",
                    "includes_media": bool(media_members),
                    "restore_mode_supported": ["overwrite"],
                }
                structure = {
                    "safe_names": names,
                    "db_members": db_members,
                    "media_members": media_members,
                    "tipo": metadata["backup_type"],
                }
            validate_archive_checksum(filepath, metadata)
            if record and record.checksum and not validate_checksum(filepath, record.checksum):
                raise BackupRestoreError("El archivo del respaldo no coincide con el checksum registrado.")
            validate_engine_compatibility(
                metadata,
                engine.get_engine_name(),
                allow_cross_engine=config.permitir_restore_cross_engine,
            )
            if not engine.can_restore_from(metadata) and not config.permitir_restore_cross_engine:
                raise BackupRestoreError("El engine actual no admite restore directo desde ese motor.")

            restore_result = None
            db_member = structure["db_members"][0] if structure["db_members"] else None
            if db_member:
                if hasattr(engine, "restore_database_snapshot"):
                    restore_db_path = engine.restore_database_snapshot(zf, db_member, temp_dir)
                    restore_result = {"db_path": restore_db_path}
                else:
                    payload_path = os.path.join(temp_dir, os.path.basename(db_member))
                    with zip_file_member_to_path(zf, db_member, payload_path):
                        pass
                    engine.validate_backup_payload(payload_path)
                    restore_result = engine.restore_database_backup(temp_dir, payload_path)
                restore_db_path = (restore_result or {}).get("db_path")
                if restore_db_path:
                    engine.merge_history_after_restore(historial_prev, restore_db_path)
                engine.post_restore_checks(restore_result)

            media_members = structure["media_members"]
            if media_members:
                media_engine.validate_media_members(media_members)
                media_engine.restore_media_from_zip(zf, media_members, mode=mode)
                media_engine.verify_media_root_access()
    except Exception as exc:
        if record:
            mark_failed(record, exc, notas=record.notas, action="fallido_restauracion")
        raise BackupRestoreError(str(exc)) from exc
    finally:
        cleanup_temp_dir(temp_dir)

    if record:
        mark_restored(record)
    return {
        "ok": True,
        "safety_backup": safety_record.pk if safety_record else None,
        "mode": mode,
    }


class zip_file_member_to_path:
    def __init__(self, zip_file, member_name, target_path):
        self.zip_file = zip_file
        self.member_name = member_name
        self.target_path = target_path

    def __enter__(self):
        os.makedirs(os.path.dirname(self.target_path), exist_ok=True)
        with self.zip_file.open(self.member_name) as src, open(self.target_path, "wb") as dst:
            dst.write(src.read())
        return self.target_path

    def __exit__(self, exc_type, exc, tb):
        return False
