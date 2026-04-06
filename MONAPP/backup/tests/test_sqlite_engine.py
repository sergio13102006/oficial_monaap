import os
import sqlite3
import tempfile

from django.test import TestCase

from backup.services.engines.sqlite_engine import SQLiteBackupEngine


class LimpiezaHistorialBackupSqliteTests(TestCase):
    def test_limpia_el_historial_del_modulo_backup_en_sqlite(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as tmp:
            temp_db = tmp.name

        try:
            conn = sqlite3.connect(temp_db)
            try:
                cur = conn.cursor()
                cur.execute(
                    "CREATE TABLE backup_backuprecord (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, estado TEXT);"
                )
                cur.execute(
                    "INSERT INTO backup_backuprecord (nombre, estado) VALUES (?, ?);",
                    ("lola", "en_progreso"),
                )
                conn.commit()
            finally:
                conn.close()

            SQLiteBackupEngine().clean_backup_history_in_snapshot(temp_db)

            conn = sqlite3.connect(temp_db)
            try:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM backup_backuprecord;")
                total = cur.fetchone()[0]
            finally:
                conn.close()

            self.assertEqual(total, 0)
        finally:
            if os.path.exists(temp_db):
                os.remove(temp_db)

