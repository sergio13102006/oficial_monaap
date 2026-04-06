import os
import time
from datetime import datetime

from backup.constants import BACKUP_DB_FILENAME, BACKUP_META_FILENAME

from .engines import MediaBackupEngine, SQLiteBackupEngine
from .history_service import create_backup_record, mark_backup_failed, mark_backup_success
from .metadata_service import build_backup_metadata, serialize_backup_metadata
from .retention_service import apply_retention_policy
from backup.selectors import get_all_tables
from .storage_service import (
    build_backup_filename,
    delete_backup_file,
    ensure_backup_dir,
    get_backup_file_size,
    open_backup_zip,
)


sqlite_engine = SQLiteBackupEngine()
media_engine = MediaBackupEngine()


def create_backup(tipo, user=None, incluir_media=False, comentario="", nombre=None):
    if tipo == "base_datos":
        return create_database_backup(nombre=nombre, usuario=user, notas=comentario)
    if tipo == "media":
        return create_media_backup(nombre=nombre, usuario=user, notas=comentario)
    return create_full_backup(nombre=nombre, usuario=user, notas=comentario)


def create_database_backup(nombre=None, usuario=None, notas=""):
    return _create_backup_recorded(
        tipo="base_datos",
        nombre=nombre,
        usuario=usuario,
        notas=notas,
        include_db=True,
        include_media=False,
    )


def create_full_backup(nombre=None, usuario=None, notas=""):
    return _create_backup_recorded(
        tipo="completo",
        nombre=nombre,
        usuario=usuario,
        notas=notas,
        include_db=True,
        include_media=True,
    )


def create_media_backup(nombre=None, usuario=None, notas=""):
    return _create_backup_recorded(
        tipo="media",
        nombre=nombre,
        usuario=usuario,
        notas=notas,
        include_db=False,
        include_media=True,
    )


def _create_backup_recorded(tipo, nombre, usuario, notas, *, include_db, include_media):
    start_time = time.time()
    backup_dir = ensure_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    defaults = {
        "base_datos": f"backup_bd_{timestamp}",
        "completo": f"backup_completo_{timestamp}",
        "media": f"backup_media_{timestamp}",
    }
    nombre = (nombre or "").strip() or defaults[tipo]
    filepath = build_backup_filename(nombre)
    record = create_backup_record(nombre=nombre, tipo=tipo, usuario=usuario, notas=notas)
    temp_db = None

    try:
        with open_backup_zip(filepath, "w") as zf:
            tablas = []
            extra = {}
            if include_db:
                temp_db = os.path.join(backup_dir, f"temp_{timestamp}.sqlite3")
                sqlite_engine.create_database_snapshot(temp_db)
                sqlite_engine.clean_backup_history_in_snapshot(temp_db)
                zf.write(temp_db, BACKUP_DB_FILENAME)
                tablas = get_all_tables()
            if include_media:
                media_files = media_engine.add_media_to_zip(zf)
                extra["media_files_count"] = len(media_files)
                extra["incluye_media"] = True
                extra["total_size_files"] = sum(item["size"] for item in media_files)
            meta = build_backup_metadata(
                nombre=nombre,
                tipo=tipo,
                usuario=usuario,
                notas=notas,
                tablas=tablas,
                extra=extra,
            )
            zf.writestr(BACKUP_META_FILENAME, serialize_backup_metadata(meta))

        if temp_db and os.path.exists(temp_db):
            os.remove(temp_db)

        duration = time.time() - start_time
        file_size = get_backup_file_size(filepath)
        tablas_incluidas = ", ".join(tablas) if tablas else (
            f"{extra.get('media_files_count', 0)} archivos de media"
        )
        mark_backup_success(
            record,
            archivo=filepath,
            tamano=file_size,
            duracion_segundos=duration,
            tablas_incluidas=tablas_incluidas,
        )
        apply_retention_policy()
        return record
    except Exception as exc:
        mark_backup_failed(
            record,
            exc,
            notas=notas,
            duracion_segundos=time.time() - start_time,
        )
        if temp_db and os.path.exists(temp_db):
            os.remove(temp_db)
        if os.path.exists(filepath):
            delete_backup_file(filepath)
        raise
