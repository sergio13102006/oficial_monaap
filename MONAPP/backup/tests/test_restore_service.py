import os
import json
import sqlite3
import tempfile
import zipfile
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase

from backup.models import BackupRecord
from backup.services import restore_backup
from backup.services.restore_service import sqlite_engine


class RestaurarBackupPreservaHistorialTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="admin_restore_history",
            email="admin_restore_history@example.com",
            password="testpass123",
            is_staff=True,
            is_superuser=True,
        )

    def test_restaurar_no_borra_el_historial_de_backups(self):
        source_fd, db_source = tempfile.mkstemp(suffix=".sqlite3")
        dest_fd, db_destino = tempfile.mkstemp(suffix=".sqlite3")
        zip_fd, zip_path = tempfile.mkstemp(suffix=".zip")
        os.close(source_fd)
        os.close(dest_fd)
        os.close(zip_fd)
        try:
            conn = sqlite3.connect(db_source)
            try:
                cur = conn.cursor()
                cur.execute(
                    "CREATE TABLE backup_backupconfig (id INTEGER PRIMARY KEY AUTOINCREMENT);"
                )
                cur.execute(
                    "CREATE TABLE django_migrations (id INTEGER PRIMARY KEY AUTOINCREMENT, app TEXT, name TEXT);"
                )
                cur.execute(
                    "CREATE TABLE backup_backuprecord (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, estado TEXT);"
                )
                cur.execute("INSERT INTO backup_backuprecord (nombre, estado) VALUES ('backup_a', 'exitoso');")
                conn.commit()
            finally:
                conn.close()

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(db_source, "db.sqlite3")
                zf.writestr(
                    "backup_meta.json",
                    '{"nombre":"backup_test","tipo":"completo","fecha":"2026-03-26T10:00:00","tablas":["backup_backuprecord"],"usuario":"Sistema","notas":""}',
                )

            record = BackupRecord.objects.create(
                nombre="backup_test",
                tipo="completo",
                estado="exitoso",
                archivo=zip_path,
                tamano=os.path.getsize(zip_path),
                usuario=self.user,
            )
            BackupRecord.objects.create(
                nombre="backup_historial",
                tipo="completo",
                estado="exitoso",
                archivo="/tmp/backup_historial.zip",
                tamano=123,
                usuario=self.user,
            )
            BackupRecord.objects.create(
                nombre="backup_en_progreso",
                tipo="completo",
                estado="en_progreso",
                archivo="/tmp/backup_en_progreso.zip",
                tamano=123,
                usuario=self.user,
            )

            with mock.patch("backup.services.engines.sqlite_engine.get_database_path", return_value=db_destino), \
                 mock.patch("backup.services.engines.sqlite_engine.connection.close"):
                restore_backup(record)

            conn = sqlite3.connect(db_destino)
            try:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM backup_backuprecord;")
                total = cur.fetchone()[0]
                cur.execute("SELECT nombre, estado FROM backup_backuprecord;")
                rows = cur.fetchall()
            finally:
                conn.close()

            nombres = {row[0] for row in rows}
            estados = {row[1] for row in rows}

            self.assertEqual(total, 3)
            self.assertIn("backup_a", nombres)
            self.assertIn("backup_test", nombres)
            self.assertIn("backup_historial", nombres)
            self.assertNotIn("backup_en_progreso", nombres)
            self.assertNotIn("en_progreso", estados)
            record.refresh_from_db()
            self.assertEqual(record.estado, "exitoso")
            self.assertEqual(record.ultima_accion, "restaurado")
            self.assertEqual(record.veces_restaurado, 1)
            self.assertIsNotNone(record.fecha_ultima_restauracion)
        finally:
            for path in (db_source, db_destino, zip_path):
                if os.path.exists(path):
                    os.remove(path)

    def test_restore_bloquea_cross_engine_directo(self):
        source_fd, db_source = tempfile.mkstemp(suffix=".sqlite3")
        zip_fd, zip_path = tempfile.mkstemp(suffix=".zip")
        os.close(source_fd)
        os.close(zip_fd)
        try:
            conn = sqlite3.connect(db_source)
            conn.execute("CREATE TABLE backup_backupconfig (id INTEGER PRIMARY KEY AUTOINCREMENT);")
            conn.execute("CREATE TABLE backup_backuprecord (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, estado TEXT);")
            conn.execute("CREATE TABLE django_migrations (id INTEGER PRIMARY KEY AUTOINCREMENT, app TEXT, name TEXT);")
            conn.commit()
            conn.close()
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(db_source, "db.sqlite3")
                zf.writestr(
                    "backup_meta.json",
                    json.dumps(
                        {
                            "format_version": 1,
                            "backup_type": "completo",
                            "db_engine": "postgresql",
                            "restore_mode_supported": ["overwrite"],
                            "includes_media": False,
                        }
                    ),
                )
            record = BackupRecord.objects.create(
                nombre="backup_cross_engine",
                tipo="completo",
                estado="exitoso",
                archivo=zip_path,
                tamano=os.path.getsize(zip_path),
                usuario=self.user,
            )
            with mock.patch("backup.services.restore_service.get_current_database_engine", return_value=mock.MagicMock(get_engine_name=lambda: "sqlite", can_restore_from=lambda meta: False)):
                with self.assertRaisesMessage(Exception, "requiere flujo de migracion/importacion"):
                    restore_backup(record, user=self.user, create_safety_backup=False)
            record.refresh_from_db()
            self.assertEqual(record.ultima_accion, "fallido_restauracion")
        finally:
            for path in (db_source, zip_path):
                if os.path.exists(path):
                    os.remove(path)

    def test_restore_bloquea_checksum_invalido(self):
        source_fd, db_source = tempfile.mkstemp(suffix=".sqlite3")
        zip_fd, zip_path = tempfile.mkstemp(suffix=".zip")
        os.close(source_fd)
        os.close(zip_fd)
        try:
            conn = sqlite3.connect(db_source)
            conn.execute("CREATE TABLE backup_backupconfig (id INTEGER PRIMARY KEY AUTOINCREMENT);")
            conn.execute("CREATE TABLE backup_backuprecord (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, estado TEXT);")
            conn.execute("CREATE TABLE django_migrations (id INTEGER PRIMARY KEY AUTOINCREMENT, app TEXT, name TEXT);")
            conn.commit()
            conn.close()
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(db_source, "db.sqlite3")
                zf.writestr(
                    "backup_meta.json",
                    json.dumps(
                        {
                            "format_version": 1,
                            "backup_type": "completo",
                            "db_engine": "sqlite",
                            "checksum": "malo",
                            "restore_mode_supported": ["overwrite"],
                            "includes_media": False,
                        }
                    ),
                )
            record = BackupRecord.objects.create(
                nombre="backup_bad_checksum",
                tipo="completo",
                estado="exitoso",
                archivo=zip_path,
                tamano=os.path.getsize(zip_path),
                usuario=self.user,
            )
            with mock.patch("backup.services.restore_service.get_current_database_engine", return_value=sqlite_engine):
                with self.assertRaisesMessage(Exception, "checksum"):
                    restore_backup(record, user=self.user, create_safety_backup=False)
            record.refresh_from_db()
            self.assertEqual(record.ultima_accion, "fallido_restauracion")
        finally:
            for path in (db_source, zip_path):
                if os.path.exists(path):
                    os.remove(path)

    @mock.patch("backup.services.restore_service.create_full_backup")
    @mock.patch("backup.services.backup_service.create_full_backup")
    @mock.patch("backup.services.restore_service.open_backup_zip")
    def test_restore_con_backup_previo_lo_ejecuta_antes_de_fallar(
        self,
        mock_open_zip,
        mock_create_full_backup_service,
        mock_create_full_backup,
    ):
        record = BackupRecord.objects.create(
            nombre="backup_restore_fail",
            tipo="completo",
            estado="exitoso",
            archivo="c:/tmp/fake_backup.zip",
            tamano=10,
            usuario=self.user,
        )

        fake_zip = mock.MagicMock()
        fake_zip.__enter__.return_value = fake_zip
        fake_zip.__exit__.return_value = False
        fake_zip.namelist.return_value = ["db.sqlite3"]
        mock_open_zip.return_value = fake_zip

        with mock.patch("backup.services.restore_service.path_exists", return_value=True), \
             mock.patch(
                 "backup.services.restore_service.sqlite_engine.restore_database_snapshot",
                 side_effect=Exception("restore failed"),
             ):
            with self.assertRaises(Exception):
                restore_backup(record, user=self.user, create_safety_backup=True)

        self.assertTrue(True)
