import os
import sqlite3
import tempfile
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from backup.services import create_database_backup


@override_settings(MEDIA_ROOT="")
class BackupServiceTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="admin_backup_service",
            email="admin_backup_service@example.com",
            password="testpass123",
            is_staff=True,
            is_superuser=True,
        )

    def test_crea_backup_de_base_datos_y_registra_estado_exitoso(self):
        fd, temp_db = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        try:
            conn = sqlite3.connect(temp_db)
            conn.execute("CREATE TABLE ejemplo (id INTEGER PRIMARY KEY AUTOINCREMENT);")
            conn.commit()
            conn.close()

            with mock.patch(
                "backup.services.engines.sqlite_engine.get_database_path",
                return_value=temp_db,
            ):
                record = create_database_backup(
                    nombre="backup_test_unit", usuario=self.user
                )

            self.assertEqual(record.estado, "exitoso")
            self.assertTrue(record.archivo)
            self.assertTrue(os.path.exists(record.archivo))
        finally:
            if os.path.exists(temp_db):
                os.remove(temp_db)
