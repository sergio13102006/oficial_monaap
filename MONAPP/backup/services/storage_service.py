import os
import shutil
import tempfile
import zipfile
import hashlib
from datetime import datetime
from pathlib import Path

from django.conf import settings

from backup.exceptions import BackupStorageError
from .config_service import get_backup_config


def get_backup_dir():
    config = get_backup_config()
    backup_dir = config.ruta_backups or os.path.join(settings.BASE_DIR, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir


def ensure_backup_dir():
    backup_dir = get_backup_dir()
    if not backup_dir or not os.path.exists(backup_dir):
        raise BackupStorageError(f"Directorio de backups no accesible: {backup_dir}")
    return backup_dir


def build_backup_filename(nombre_base, extension=".zip"):
    backup_dir = ensure_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{nombre_base}{extension}"
    filepath = os.path.join(backup_dir, filename)
    if os.path.exists(filepath):
        filepath = os.path.join(backup_dir, f"{nombre_base}_{timestamp}{extension}")
    return filepath


def create_temp_file(suffix="", prefix="tmp_", dirpath=None):
    if dirpath and not os.path.isdir(dirpath):
        dirpath = ensure_backup_dir()
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=suffix, prefix=prefix, dir=dirpath
    ) as temp_file:
        return temp_file.name


def delete_backup_file(path):
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError as exc:
            raise BackupStorageError(str(exc)) from exc


def copy_file(src, dst):
    try:
        shutil.copy2(src, dst)
    except OSError as exc:
        raise BackupStorageError(str(exc)) from exc


def get_backup_file_size(path):
    return os.path.getsize(path) if path and os.path.exists(path) else 0


def calculate_checksum(path, algorithm="sha256"):
    if not path or not os.path.exists(path):
        return ""
    hasher = hashlib.new(algorithm)
    with open(path, "rb") as src:
        for chunk in iter(lambda: src.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def calculate_zip_content_checksum(path, algorithm="sha256", skip_members=None):
    if not path or not os.path.exists(path):
        return ""
    skip_members = set(skip_members or [])
    hasher = hashlib.new(algorithm)
    with zipfile.ZipFile(path, "r") as zf:
        for name in sorted(zf.namelist()):
            if name in skip_members or name.endswith("/"):
                continue
            hasher.update(name.encode("utf-8"))
            with zf.open(name) as src:
                for chunk in iter(lambda: src.read(1024 * 1024), b""):
                    hasher.update(chunk)
    return hasher.hexdigest()


def validate_checksum(path, expected_checksum, algorithm="sha256"):
    if not expected_checksum:
        return True
    current = calculate_checksum(path, algorithm=algorithm)
    return current == expected_checksum


def open_backup_zip(path, mode="r"):
    try:
        return zipfile.ZipFile(path, mode, zipfile.ZIP_DEFLATED)
    except (OSError, zipfile.BadZipFile) as exc:
        raise BackupStorageError(str(exc)) from exc


def save_uploaded_file(uploaded_file, suffix=".zip"):
    backup_dir = ensure_backup_dir()
    temp_path = create_temp_file(suffix=suffix, prefix="upload_", dirpath=backup_dir)
    with open(temp_path, "wb") as temp_file:
        for chunk in uploaded_file.chunks():
            temp_file.write(chunk)
    return temp_path


def save_backup_file(src_path, nombre_base):
    filepath = build_backup_filename(nombre_base)
    copy_file(src_path, filepath)
    return filepath


def create_temp_dir(prefix="backup_tmp_"):
    return ensure_backup_dir()


def cleanup_temp_dir(path):
    if path and os.path.exists(path) and os.path.normcase(path) != os.path.normcase(ensure_backup_dir()):
        shutil.rmtree(path, ignore_errors=True)


def path_exists(path):
    return bool(path) and Path(path).exists()
