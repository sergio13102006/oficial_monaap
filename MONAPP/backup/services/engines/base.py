class BackupEngine:
    def get_engine_name(self):
        raise NotImplementedError

    def supports_current_database(self):
        raise NotImplementedError

    def create_database_backup(self, temp_dir):
        raise NotImplementedError

    def restore_database_backup(self, temp_dir, payload_path):
        raise NotImplementedError

    def validate_backup_payload(self, payload_path):
        raise NotImplementedError

    def validate_restore_target(self):
        raise NotImplementedError

    def can_restore_from(self, metadata):
        raise NotImplementedError

    def post_restore_checks(self, restore_result=None):
        raise NotImplementedError
