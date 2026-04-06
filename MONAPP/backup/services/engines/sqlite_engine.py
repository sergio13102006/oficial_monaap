import os
import sqlite3

from django.db import connection

from backup.models import BackupRecord
from backup.exceptions import BackupEngineError
from backup.selectors import get_database_path


def _backup_history_key(data):
    archivo = (data.get("archivo") or "").strip()
    if archivo:
        return ("archivo", archivo)
    return (
        "fallback",
        data.get("nombre") or "",
        data.get("tipo") or "",
        data.get("estado") or "",
        str(data.get("fecha_creacion") or ""),
        str(data.get("usuario_id") or ""),
        str(data.get("tamano") or 0),
    )


class SQLiteBackupEngine:
    def supports_current_database(self):
        return str(get_database_path()).endswith(".sqlite3")

    def create_database_snapshot(self, temp_db_path):
        db_path = str(get_database_path())
        if not os.path.exists(db_path):
            raise BackupEngineError(f"Base de datos no encontrada: {db_path}")
        source = sqlite3.connect(db_path)
        dest = sqlite3.connect(temp_db_path)
        try:
            source.backup(dest)
        finally:
            source.close()
            dest.close()
        if not os.path.exists(temp_db_path):
            raise BackupEngineError(
                "No se pudo crear la copia temporal de la base de datos."
            )
        return temp_db_path

    def clean_backup_history_in_snapshot(self, db_path):
        if not db_path or not os.path.exists(db_path):
            return
        try:
            conn = sqlite3.connect(db_path)
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='backup_backuprecord';"
                )
                if cur.fetchone():
                    cur.execute('DELETE FROM "backup_backuprecord";')
                    conn.commit()
            finally:
                conn.close()
        except Exception:
            pass

    def restore_database_snapshot(self, zip_file, member_name, backup_dir):
        db_path = str(get_database_path())
        connection.close()
        temp_db = os.path.join(backup_dir, "restore_temp.sqlite3")
        with zip_file.open(member_name) as src, open(temp_db, "wb") as dst:
            dst.write(src.read())
        from ..storage_service import copy_file, delete_backup_file

        copy_file(temp_db, db_path)
        delete_backup_file(temp_db)
        return db_path

    def merge_history_after_restore(self, historial, db_path):
        if not historial or not db_path or not os.path.exists(db_path):
            return 0

        from django.contrib.auth import get_user_model

        user_ids_validos = set(get_user_model().objects.values_list("id", flat=True))
        existentes = set()

        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            cur.execute(f'PRAGMA table_info("{BackupRecord._meta.db_table}")')
            columnas_existentes = [row[1] for row in cur.fetchall()]
            if not columnas_existentes:
                return 0
            columnas_deseadas = [
                "nombre",
                "tipo",
                "estado",
                "archivo",
                "tamano",
                "fecha_creacion",
                "usuario_id",
                "notas",
                "es_automatico",
                "tablas_incluidas",
                "duracion_segundos",
            ]
            columnas_insertables = [c for c in columnas_deseadas if c in columnas_existentes]
            if not columnas_insertables:
                return 0
            cur.execute(
                f'SELECT {", ".join(columnas_insertables)} FROM "{BackupRecord._meta.db_table}"'
            )
            for row in cur.fetchall():
                data_row = {col: row[idx] for idx, col in enumerate(columnas_insertables)}
                existentes.add(_backup_history_key(data_row))
        finally:
            conn.close()

        nuevos = []
        for data in historial:
            if data.get("estado") == "en_progreso":
                continue
            clave = _backup_history_key(data)
            if clave in existentes:
                continue
            usuario_id = data.get("usuario_id")
            if usuario_id not in user_ids_validos:
                usuario_id = None
            nuevos.append(
                BackupRecord(
                    nombre=data.get("nombre") or "",
                    tipo=data.get("tipo") or "completo",
                    estado=data.get("estado") or "exitoso",
                    archivo=data.get("archivo"),
                    tamano=data.get("tamano") or 0,
                    fecha_creacion=data.get("fecha_creacion"),
                    usuario_id=usuario_id,
                    notas=data.get("notas") or "",
                    es_automatico=bool(data.get("es_automatico")),
                    tablas_incluidas=data.get("tablas_incluidas") or "",
                    duracion_segundos=data.get("duracion_segundos") or 0,
                )
            )

        if not nuevos:
            return 0

        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            cur.execute(f'PRAGMA table_info("{BackupRecord._meta.db_table}")')
            columnas_existentes = [row[1] for row in cur.fetchall()]
            columnas_deseadas = [
                "nombre",
                "tipo",
                "estado",
                "archivo",
                "tamano",
                "fecha_creacion",
                "usuario_id",
                "notas",
                "es_automatico",
                "tablas_incluidas",
                "duracion_segundos",
            ]
            columnas_insertables = [c for c in columnas_deseadas if c in columnas_existentes]
            for item in nuevos:
                valores = []
                for columna in columnas_insertables:
                    if columna == "fecha_creacion":
                        valores.append(item.fecha_creacion.isoformat(sep=" "))
                    elif columna == "es_automatico":
                        valores.append(1 if item.es_automatico else 0)
                    else:
                        valores.append(getattr(item, columna))
                cur.execute(
                    f'INSERT INTO "{BackupRecord._meta.db_table}" '
                    f'({", ".join(columnas_insertables)}) VALUES ({", ".join(["?"] * len(columnas_insertables))})',
                    tuple(valores),
                )
            conn.commit()
        finally:
            conn.close()
        return len(nuevos)

    def validate_restored_database(self, db_path):
        if not db_path or not os.path.exists(db_path):
            raise BackupEngineError("La base restaurada no existe.")
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA integrity_check;")
            result = cur.fetchone()
            if not result or result[0].lower() != "ok":
                raise BackupEngineError("La base restaurada no pasó la validación.")
        finally:
            conn.close()
        return True
