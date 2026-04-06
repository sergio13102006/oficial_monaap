import io
import json
import tempfile
import zipfile
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from backup.exceptions import BackupValidationError
from backup.services.validation_service import (
    is_safe_zip_member,
    normalize_zip_member,
    validate_archive_checksum,
    validate_backup_metadata,
    validate_engine_compatibility,
)


class ValidationServiceTests(TestCase):
    def test_bloquea_rutas_peligrosas(self):
        with self.assertRaises(BackupValidationError):
            normalize_zip_member("../db.sqlite3")
        self.assertFalse(is_safe_zip_member("../db.sqlite3"))

    def test_valida_tipo_de_backup(self):
        self.assertEqual(validate_backup_metadata({"tipo": "completo"}), "completo")
        with self.assertRaises(BackupValidationError):
            validate_backup_metadata({"tipo": "otro"})

    def test_bloquea_restore_cross_engine_directo(self):
        with self.assertRaises(BackupValidationError):
            validate_engine_compatibility(
                {"db_engine": "postgresql"},
                "sqlite",
                allow_cross_engine=True,
            )

    def test_detecta_checksum_invalido(self):
        fd, zip_path = tempfile.mkstemp(suffix=".zip")
        try:
            import os
            os.close(fd)
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("db.sqlite3", b"payload")
                zf.writestr(
                    "backup_meta.json",
                    json.dumps(
                        {
                            "format_version": 1,
                            "backup_type": "base_datos",
                            "db_engine": "sqlite",
                            "checksum": "invalido",
                        }
                    ),
                )
            with self.assertRaises(BackupValidationError):
                validate_archive_checksum(zip_path, {"checksum": "invalido"})
        finally:
            import os
            if os.path.exists(zip_path):
                os.remove(zip_path)
