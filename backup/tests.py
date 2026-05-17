import os
import sqlite3
import tempfile
import zipfile
from types import SimpleNamespace
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from backup.models import BackupRecord
from backup.services import _limpiar_historial_backup_sqlite, restaurar_backup


class ImportarBackupViewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='admin_backup',
            email='admin@example.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(self.user)

    @mock.patch('backup.views.restaurar_backup')
    @mock.patch('backup.views.importar_backup_desde_archivo')
    def test_importar_con_restauracion_ejecuta_ambos_pasos(
        self,
        mock_importar,
        mock_restaurar,
    ):
        record = SimpleNamespace(nombre='backup_prueba')
        mock_importar.return_value = record

        archivo = SimpleUploadedFile(
            'backup_prueba.zip',
            b'contenido-falso',
            content_type='application/zip',
        )

        response = self.client.post(
            reverse('backup:importar'),
            {
                'archivo_backup': archivo,
                'notas': 'Prueba',
                'restaurar_despues': 'on',
            },
        )

        self.assertEqual(response.status_code, 302)
        mock_importar.assert_called_once()
        mock_restaurar.assert_called_once_with(record)

    @mock.patch('backup.views.restaurar_backup')
    @mock.patch('backup.views.importar_backup_desde_archivo')
    def test_importar_sin_restauracion_solo_registra_el_backup(
        self,
        mock_importar,
        mock_restaurar,
    ):
        record = SimpleNamespace(nombre='backup_prueba')
        mock_importar.return_value = record

        archivo = SimpleUploadedFile(
            'backup_prueba.zip',
            b'contenido-falso',
            content_type='application/zip',
        )

        response = self.client.post(
            reverse('backup:importar'),
            {
                'archivo_backup': archivo,
                'notas': 'Prueba',
            },
        )

        self.assertEqual(response.status_code, 302)
        mock_importar.assert_called_once()
        mock_restaurar.assert_not_called()


class LimpiezaHistorialBackupSqliteTests(TestCase):
    def test_limpia_el_historial_del_modulo_backup_en_sqlite(self):
        with tempfile.NamedTemporaryFile(suffix='.sqlite3', delete=False) as tmp:
            temp_db = tmp.name

        try:
            conn = sqlite3.connect(temp_db)
            try:
                cur = conn.cursor()
                cur.execute(
                    'CREATE TABLE backup_backuprecord (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, estado TEXT);'
                )
                cur.execute(
                    "INSERT INTO backup_backuprecord (nombre, estado) VALUES (?, ?);",
                    ('lola', 'en_progreso'),
                )
                conn.commit()
            finally:
                conn.close()

            _limpiar_historial_backup_sqlite(temp_db)

            conn = sqlite3.connect(temp_db)
            try:
                cur = conn.cursor()
                cur.execute('SELECT COUNT(*) FROM backup_backuprecord;')
                total = cur.fetchone()[0]
            finally:
                conn.close()

            self.assertEqual(total, 0)
        finally:
            if os.path.exists(temp_db):
                os.remove(temp_db)


class RestaurarBackupPreservaHistorialTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='admin_restore_history',
            email='admin_restore_history@example.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True,
        )

    def test_restaurar_no_borra_el_historial_de_backups(self):
        source_fd, db_source = tempfile.mkstemp(suffix='.sqlite3')
        dest_fd, db_destino = tempfile.mkstemp(suffix='.sqlite3')
        zip_fd, zip_path = tempfile.mkstemp(suffix='.zip')
        os.close(source_fd)
        os.close(dest_fd)
        os.close(zip_fd)
        try:
            conn = sqlite3.connect(db_source)
            try:
                cur = conn.cursor()
                cur.execute(
                    'CREATE TABLE backup_backuprecord (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, estado TEXT);'
                )
                cur.execute("INSERT INTO backup_backuprecord (nombre, estado) VALUES ('backup_a', 'exitoso');")
                conn.commit()
            finally:
                conn.close()

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(db_source, 'db.sqlite3')
                zf.writestr(
                    'backup_meta.json',
                    '{"nombre":"backup_test","tipo":"completo","fecha":"2026-03-26T10:00:00","tablas":["backup_backuprecord"],"usuario":"Sistema","notas":""}'
                )

            record = BackupRecord.objects.create(
                nombre='backup_test',
                tipo='completo',
                estado='exitoso',
                archivo=zip_path,
                tamano=os.path.getsize(zip_path),
                usuario=self.user,
            )
            BackupRecord.objects.create(
                nombre='backup_historial',
                tipo='completo',
                estado='exitoso',
                archivo='/tmp/backup_historial.zip',
                tamano=123,
                usuario=self.user,
            )
            BackupRecord.objects.create(
                nombre='backup_en_progreso',
                tipo='completo',
                estado='en_progreso',
                archivo='/tmp/backup_en_progreso.zip',
                tamano=123,
                usuario=self.user,
            )

            with mock.patch('backup.services.get_database_path', return_value=db_destino), \
                 mock.patch('backup.services.get_backup_dir', return_value=os.path.dirname(db_destino)), \
                 mock.patch('backup.services.connection.close'):
                restaurar_backup(record)

            conn = sqlite3.connect(db_destino)
            try:
                cur = conn.cursor()
                cur.execute('SELECT COUNT(*) FROM backup_backuprecord;')
                total = cur.fetchone()[0]
                cur.execute('SELECT nombre, estado FROM backup_backuprecord;')
                rows = cur.fetchall()
            finally:
                conn.close()

            nombres = {row[0] for row in rows}
            estados = {row[1] for row in rows}

            self.assertEqual(total, 3)
            self.assertIn('backup_a', nombres)
            self.assertIn('backup_test', nombres)
            self.assertIn('backup_historial', nombres)
            self.assertNotIn('backup_en_progreso', nombres)
            self.assertNotIn('en_progreso', estados)
        finally:
            for path in (db_source, db_destino, zip_path):
                if os.path.exists(path):
                    os.remove(path)
