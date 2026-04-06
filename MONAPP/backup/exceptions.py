class BackupError(Exception):
    """Base exception for the backup module."""


class BackupValidationError(BackupError):
    """Raised when a backup file or payload is invalid."""


class BackupRestoreError(BackupError):
    """Raised when restoring a backup fails."""


class BackupImportError(BackupError):
    """Raised when importing a backup fails."""


class BackupStorageError(BackupError):
    """Raised when storage operations fail."""


class BackupEngineError(BackupError):
    """Raised when an engine fails during backup or restore operations."""

