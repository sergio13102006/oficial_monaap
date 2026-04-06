from backup.constants import BACKUP_DB_FILENAME
from backup.exceptions import BackupRestoreError

from .backup_service import create_full_backup
from .engines import MediaBackupEngine, SQLiteBackupEngine
from .history_service import mark_backup_restored, snapshot_current_backup_history
from .storage_service import ensure_backup_dir, open_backup_zip, path_exists
from .validation_service import media_relative_path, normalize_zip_member


sqlite_engine = SQLiteBackupEngine()
media_engine = MediaBackupEngine()


def restore_backup(record_or_path, user=None, mode="overwrite", create_safety_backup=False):
    record = getattr(record_or_path, "archivo", None) and record_or_path or None
    filepath = record.archivo if record else str(record_or_path)
    if not path_exists(filepath):
        raise FileNotFoundError("El archivo de backup no existe.")

    if create_safety_backup:
        create_full_backup(
            nombre=None,
            usuario=user,
            notas="Backup de seguridad previo a restauración",
        )

    backup_dir = ensure_backup_dir()
    historial_prev = snapshot_current_backup_history()

    try:
        with open_backup_zip(filepath, "r") as zf:
            names = zf.namelist()
            db_member = next(
                (
                    normalize_zip_member(name)
                    for name in names
                    if normalize_zip_member(name)
                    and normalize_zip_member(name).endswith(BACKUP_DB_FILENAME)
                ),
                None,
            )
            if db_member:
                db_path = sqlite_engine.restore_database_snapshot(zf, db_member, backup_dir)
                sqlite_engine.merge_history_after_restore(historial_prev, db_path)
                sqlite_engine.validate_restored_database(db_path)

            media_files = [
                normalize_zip_member(name)
                for name in names
                if normalize_zip_member(name)
                and media_relative_path(normalize_zip_member(name)) is not None
            ]
            if media_files:
                media_engine.restore_media_from_zip(zf, media_files, mode=mode)
    except Exception as exc:
        raise BackupRestoreError(str(exc)) from exc

    if record:
        mark_backup_restored(record)
    return True
