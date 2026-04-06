from backup.constants import DB_ENGINE_POSTGRES
from backup.exceptions import BackupEngineError, BackupValidationError

from .base import BackupEngine


class PostgresBackupEngine(BackupEngine):
    def get_engine_name(self):
        return DB_ENGINE_POSTGRES

    def supports_current_database(self):
        return False

    def create_database_backup(self, temp_dir):
        raise BackupEngineError("El engine PostgreSQL todavia no implementa backup logico.")

    def restore_database_backup(self, temp_dir, payload_path):
        raise BackupEngineError("El engine PostgreSQL todavia no implementa restore logico.")

    def validate_backup_payload(self, payload_path):
        if not payload_path:
            raise BackupValidationError("El payload de PostgreSQL no es valido.")
        return True

    def validate_restore_target(self):
        return True

    def can_restore_from(self, metadata):
        return (metadata or {}).get("db_engine") == DB_ENGINE_POSTGRES

    def post_restore_checks(self, restore_result=None):
        raise BackupEngineError("El engine PostgreSQL todavia no implementa chequeos post-restore.")
