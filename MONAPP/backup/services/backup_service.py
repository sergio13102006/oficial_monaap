import os
import time
from datetime import datetime

from backup.constants import (
    BACKUP_ACTION_SECURITY,
    BACKUP_META_FILENAME,
    BACKUP_TYPE_DB,
    BACKUP_TYPE_FULL,
    BACKUP_TYPE_MEDIA,
)

from .config_service import get_backup_config
from .engines import get_current_database_engine, media_engine
from .history_service import create_event_record, mark_failed, mark_success
from .metadata_service import build_backup_metadata, serialize_backup_metadata
from .retention_service import apply_retention_policy
from .storage_service import (
    build_backup_filename,
    calculate_checksum,
    calculate_zip_content_checksum,
    cleanup_temp_dir,
    create_temp_dir,
    get_backup_file_size,
    open_backup_zip,
)


def create_backup(tipo, user=None, incluir_media=False, comentario="", nombre=None):
    if tipo == BACKUP_TYPE_DB:
        return create_database_backup(nombre=nombre, usuario=user, notas=comentario)
    if tipo == BACKUP_TYPE_MEDIA:
        return create_media_backup(nombre=nombre, usuario=user, notas=comentario)
    return create_full_backup(nombre=nombre, usuario=user, notas=comentario, include_media=incluir_media)


def create_database_backup(nombre=None, usuario=None, notas="", es_backup_seguridad=False, backup_padre=None):
    return _create_backup_recorded(
        tipo=BACKUP_TYPE_DB,
        nombre=nombre,
        usuario=usuario,
        notas=notas,
        include_db=True,
        include_media=False,
        es_backup_seguridad=es_backup_seguridad,
        backup_padre=backup_padre,
    )


def create_full_backup(nombre=None, usuario=None, notas="", include_media=None, es_backup_seguridad=False, backup_padre=None):
    config = get_backup_config()
    return _create_backup_recorded(
        tipo=BACKUP_TYPE_FULL,
        nombre=nombre,
        usuario=usuario,
        notas=notas,
        include_db=True,
        include_media=config.incluir_media if include_media is None else include_media,
        es_backup_seguridad=es_backup_seguridad,
        backup_padre=backup_padre,
    )


def create_media_backup(nombre=None, usuario=None, notas="", es_backup_seguridad=False, backup_padre=None):
    return _create_backup_recorded(
        tipo=BACKUP_TYPE_MEDIA,
        nombre=nombre,
        usuario=usuario,
        notas=notas,
        include_db=False,
        include_media=True,
        es_backup_seguridad=es_backup_seguridad,
        backup_padre=backup_padre,
    )


def _create_backup_recorded(tipo, nombre, usuario, notas, *, include_db, include_media, es_backup_seguridad, backup_padre):
    start_time = time.time()
    temp_dir = create_temp_dir(prefix="backup_build_")
    engine = get_current_database_engine()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    defaults = {
        BACKUP_TYPE_DB: f"backup_bd_{timestamp}",
        BACKUP_TYPE_FULL: f"backup_completo_{timestamp}",
        BACKUP_TYPE_MEDIA: f"backup_media_{timestamp}",
    }
    nombre = (nombre or "").strip() or defaults[tipo]
    filepath = build_backup_filename(nombre)
    accion = BACKUP_ACTION_SECURITY if es_backup_seguridad else "creado"
    record = create_event_record(
        nombre=nombre,
        tipo=tipo,
        usuario=usuario,
        notas=notas,
        accion=accion,
        db_engine=engine.get_engine_name(),
        incluye_media=include_media,
        es_backup_seguridad=es_backup_seguridad,
        backup_padre=backup_padre,
    )

    try:
        payload = None
        tablas_incluidas = ""

        with open_backup_zip(filepath, "w") as zf:
            if include_db:
                payload = engine.create_database_backup(temp_dir)
                payload_path = payload["payload_path"]
                zf.write(payload_path, payload.get("member_name") or os.path.basename(payload_path))
                tablas_incluidas = "Base de datos"
            if include_media:
                media_files = media_engine.create_media_payload()
                for item in media_files:
                    zf.write(item["file_path"], item["arc_name"])
                tablas_incluidas = (
                    f"{tablas_incluidas}, media" if tablas_incluidas else f"{len(media_files)} archivos de media"
                )

        checksum = calculate_zip_content_checksum(filepath, skip_members={BACKUP_META_FILENAME})
        with open_backup_zip(filepath, "a") as zf:
            metadata = build_backup_metadata(
                nombre=nombre,
                tipo=tipo,
                usuario=usuario,
                notas=notas,
                db_engine=engine.get_engine_name(),
                includes_media=include_media,
                checksum=checksum,
                is_security_backup=es_backup_seguridad,
                extra={
                    "origen": "local",
                    "payload_member": payload.get("member_name") if payload else "",
                },
            )
            zf.writestr(BACKUP_META_FILENAME, serialize_backup_metadata(metadata))

        duration = time.time() - start_time
        file_size = get_backup_file_size(filepath)
        mark_success(
            record,
            archivo=filepath,
            tamano=file_size,
            checksum=calculate_checksum(filepath),
            duracion_segundos=duration,
            tablas_incluidas=tablas_incluidas,
        )
        apply_retention_policy()
        return record
    except Exception as exc:
        mark_failed(
            record,
            exc,
            notas=notas,
            duracion_segundos=time.time() - start_time,
        )
        if os.path.exists(filepath):
            os.remove(filepath)
        raise
    finally:
        cleanup_temp_dir(temp_dir)
