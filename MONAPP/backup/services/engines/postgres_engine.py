from backup.exceptions import BackupEngineError

from .base import BackupEngine


class PostgresBackupEngine(BackupEngine):
    def supports_current_database(self):
        return False

    def create_backup_payload(self, *args, **kwargs):
        raise BackupEngineError("PostgresBackupEngine aún no está implementado.")

    def restore_backup_payload(self, *args, **kwargs):
        raise BackupEngineError("PostgresBackupEngine aún no está implementado.")
