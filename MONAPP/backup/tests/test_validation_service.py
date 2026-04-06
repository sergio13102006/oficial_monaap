import io
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from backup.exceptions import BackupValidationError
from backup.services.validation_service import (
    is_safe_zip_member,
    normalize_zip_member,
    validate_backup_metadata,
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

