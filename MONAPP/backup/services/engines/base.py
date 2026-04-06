class BackupEngine:
    def supports_current_database(self):
        raise NotImplementedError

    def create_backup_payload(self, *args, **kwargs):
        raise NotImplementedError

    def restore_backup_payload(self, *args, **kwargs):
        raise NotImplementedError
