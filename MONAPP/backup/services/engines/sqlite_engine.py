import os
import sqlite3

from django.db import connection

from backup.constants import BACKUP_DB_FILENAME, DB_ENGINE_SQLITE
from backup.exceptions import BackupEngineError, BackupValidationError
from backup.models import BackupRecord
from backup.selectors import get_database_path

from .base import BackupEngine


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


class SQLiteBackupEngine(BackupEngine):
    def get_engine_name(self):
        return DB_ENGINE_SQLITE

    def supports_current_database(self):
        return str(get_database_path()).endswith(".sqlite3")

    def create_database_backup(self, temp_dir):
        db_path = str(get_database_path())
        if not os.path.exists(db_path):
            raise BackupEngineError(f"Base de datos no encontrada: {db_path}")

        os.makedirs(temp_dir, exist_ok=True)
        temp_db_path = os.path.join(temp_dir, f"temp_backup_payload_{os.getpid()}.sqlite3")
        with open(db_path, "rb") as src, open(temp_db_path, "wb") as dst:
            dst.write(src.read())

        self.clean_backup_history_in_snapshot(temp_db_path)
        self.validate_backup_payload(temp_db_path)
        return {
            "payload_path": temp_db_path,
            "member_name": BACKUP_DB_FILENAME,
        }

    def create_database_snapshot(self, temp_db_path):
        temp_dir = os.path.dirname(temp_db_path)
        payload = self.create_database_backup(temp_dir)
        if payload["payload_path"] != temp_db_path:
            with open(payload["payload_path"], "rb") as src, open(temp_db_path, "wb") as dst:
                dst.write(src.read())
        return temp_db_path

    def restore_database_backup(self, temp_dir, payload_path):
        self.validate_restore_target()
        self.validate_backup_payload(payload_path)

        db_path = str(get_database_path())
        connection.close()
        staged_path = os.path.join(temp_dir, f"restore_db_{os.getpid()}.sqlite3")
        with open(payload_path, "rb") as src, open(staged_path, "wb") as dst:
            dst.write(src.read())
        with open(staged_path, "rb") as src, open(db_path, "wb") as dst:
            dst.write(src.read())
        return {
            "db_path": db_path,
            "staged_path": staged_path,
        }

    def restore_database_snapshot(self, zip_file, member_name, backup_dir):
        payload_path = os.path.join(backup_dir, os.path.basename(member_name))
        with zip_file.open(member_name) as src, open(payload_path, "wb") as dst:
            dst.write(src.read())
        result = self.restore_database_backup(backup_dir, payload_path)
        return result["db_path"]

    def validate_backup_payload(self, payload_path):
        if not payload_path or not os.path.exists(payload_path):
            raise BackupValidationError("El payload SQLite no existe.")
        conn = sqlite3.connect(payload_path)
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA integrity_check;")
            result = cur.fetchone()
            if not result or result[0].lower() != "ok":
                raise BackupValidationError("El payload SQLite no pasÃ³ integrity_check.")
        finally:
            conn.close()
        return True

    def validate_restore_target(self):
        db_path = str(get_database_path())
        if not db_path:
            raise BackupEngineError("No se pudo resolver la base de datos de destino.")
        return True

    def can_restore_from(self, metadata):
        return ((metadata or {}).get("db_engine") or DB_ENGINE_SQLITE) == self.get_engine_name()

    def post_restore_checks(self, restore_result=None):
        db_path = (restore_result or {}).get("db_path") if restore_result else str(get_database_path())
        self.validate_restored_database(db_path)
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = {row[0] for row in cur.fetchall()}
            required = {"django_migrations", "backup_backupconfig", "backup_backuprecord"}
            missing = required - tables
            if missing:
                raise BackupEngineError(f"Faltan tablas criticas tras el restore: {', '.join(sorted(missing))}.")
            cur.execute('SELECT COUNT(*) FROM "backup_backupconfig";')
            cur.fetchone()
            cur.execute('SELECT COUNT(*) FROM "backup_backuprecord";')
            cur.fetchone()
        finally:
            conn.close()
        return True

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
                "ultima_accion",
                "veces_restaurado",
                "fecha_ultima_restauracion",
                "checksum",
                "db_engine",
                "incluye_media",
                "origen",
                "es_backup_seguridad",
                "backup_padre_id",
                "detalle_error",
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
                    ultima_accion=data.get("ultima_accion") or "creado",
                    veces_restaurado=data.get("veces_restaurado") or 0,
                    fecha_ultima_restauracion=data.get("fecha_ultima_restauracion"),
                    checksum=data.get("checksum") or "",
                    db_engine=data.get("db_engine") or DB_ENGINE_SQLITE,
                    incluye_media=bool(data.get("incluye_media")),
                    origen=data.get("origen") or "local",
                    es_backup_seguridad=bool(data.get("es_backup_seguridad")),
                    backup_padre_id=data.get("backup_padre_id"),
                    detalle_error=data.get("detalle_error") or "",
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
                "ultima_accion",
                "veces_restaurado",
                "fecha_ultima_restauracion",
                "checksum",
                "db_engine",
                "incluye_media",
                "origen",
                "es_backup_seguridad",
                "backup_padre_id",
                "detalle_error",
            ]
            columnas_insertables = [c for c in columnas_deseadas if c in columnas_existentes]
            for item in nuevos:
                valores = []
                for columna in columnas_insertables:
                    valor = getattr(item, columna)
                    if columna in {"fecha_creacion", "fecha_ultima_restauracion"}:
                        valor = valor.isoformat(sep=" ") if valor else None
                    elif columna in {"es_automatico", "incluye_media", "es_backup_seguridad"}:
                        valor = 1 if valor else 0
                    valores.append(valor)
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
                raise BackupEngineError("La base restaurada no pasÃ³ la validaciÃ³n.")
        finally:
            conn.close()
        return True
