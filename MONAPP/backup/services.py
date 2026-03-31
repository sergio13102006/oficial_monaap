"""
Servicio de backup para MONAPP.
Maneja la lógica de creación, restauración y gestión de backups.
"""

import os
import re
import shutil
import sqlite3
import tempfile
import time
import zipfile
import json
from datetime import datetime, timedelta

from django.conf import settings
from django.db import connection
from django.utils import timezone


def get_backup_dir():
    """Obtiene el directorio de backups, creándolo si no existe."""
    from .models import BackupConfig
    config = BackupConfig.get_config()
    if config.ruta_backups:
        backup_dir = config.ruta_backups
    else:
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir


def get_database_path():
    """Obtiene la ruta de la base de datos SQLite."""
    return settings.DATABASES['default']['NAME']


def get_all_tables():
    """Obtiene todas las tablas de la base de datos."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
        )
        return [row[0] for row in cursor.fetchall()]


def _limpiar_historial_backup_sqlite(db_path):
    """
    Elimina el historial del módulo de backup de una base SQLite.

    Esto evita que un backup completo reinyecte registros internos del propio
    módulo, como estados 'en_progreso' de copias anteriores.
    """
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
        # Si no se puede limpiar, no bloqueamos la creación/restauración.
        pass


def _snapshot_historial_backup_actual():
    """Toma una copia del historial actual de backups, excluyendo 'en_progreso'."""
    from .models import BackupRecord

    campos = (
        'nombre',
        'tipo',
        'estado',
        'archivo',
        'tamano',
        'fecha_creacion',
        'usuario_id',
        'notas',
        'es_automatico',
        'tablas_incluidas',
        'duracion_segundos',
    )
    historial = []
    for record in BackupRecord.objects.exclude(estado='en_progreso').values(*campos):
        historial.append(dict(record))
    return historial


def _backup_history_key(data):
    """Genera una clave estable para evitar duplicados al restaurar."""
    archivo = (data.get('archivo') or '').strip()
    if archivo:
        return ('archivo', archivo)
    return (
        'fallback',
        data.get('nombre') or '',
        data.get('tipo') or '',
        data.get('estado') or '',
        str(data.get('fecha_creacion') or ''),
        str(data.get('usuario_id') or ''),
        str(data.get('tamano') or 0),
    )


def _fusionar_historial_backup(historial, db_path):
    """Reintegra el historial previo en la BD restaurada."""
    if not historial:
        return 0

    if not db_path or not os.path.exists(db_path):
        return 0

    from django.contrib.auth import get_user_model
    from .models import BackupRecord

    user_ids_validos = set(get_user_model().objects.values_list('id', flat=True))
    existentes = set()

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(f'PRAGMA table_info("{BackupRecord._meta.db_table}")')
        columnas_existentes = [row[1] for row in cur.fetchall()]
        if not columnas_existentes:
            return 0

        columnas_deseadas = [
            'nombre',
            'tipo',
            'estado',
            'archivo',
            'tamano',
            'fecha_creacion',
            'usuario_id',
            'notas',
            'es_automatico',
            'tablas_incluidas',
            'duracion_segundos',
        ]
        columnas_insertables = [c for c in columnas_deseadas if c in columnas_existentes]
        if not columnas_insertables:
            return 0

        cur.execute(
            f'SELECT {", ".join(columnas_insertables)} FROM "{BackupRecord._meta.db_table}"'
        )
        for row in cur.fetchall():
            data_row = {col: row[idx] for idx, col in enumerate(columnas_insertables)}
            existentes.add(
                _backup_history_key(data_row)
            )
    finally:
        conn.close()

    nuevos = []
    for data in historial:
        if data.get('estado') == 'en_progreso':
            continue

        clave = _backup_history_key(data)
        if clave in existentes:
            continue

        usuario_id = data.get('usuario_id')
        if usuario_id not in user_ids_validos:
            usuario_id = None

        nuevos.append(BackupRecord(
            nombre=data.get('nombre') or '',
            tipo=data.get('tipo') or 'completo',
            estado=data.get('estado') or 'exitoso',
            archivo=data.get('archivo'),
            tamano=data.get('tamano') or 0,
            fecha_creacion=data.get('fecha_creacion'),
            usuario_id=usuario_id,
            notas=data.get('notas') or '',
            es_automatico=bool(data.get('es_automatico')),
            tablas_incluidas=data.get('tablas_incluidas') or '',
            duracion_segundos=data.get('duracion_segundos') or 0,
        ))

    if nuevos:
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            cur.execute(f'PRAGMA table_info("{BackupRecord._meta.db_table}")')
            columnas_existentes = [row[1] for row in cur.fetchall()]
            columnas_deseadas = [
                'nombre',
                'tipo',
                'estado',
                'archivo',
                'tamano',
                'fecha_creacion',
                'usuario_id',
                'notas',
                'es_automatico',
                'tablas_incluidas',
                'duracion_segundos',
            ]
            columnas_insertables = [c for c in columnas_deseadas if c in columnas_existentes]
            if not columnas_insertables:
                return 0

            for item in nuevos:
                valores = []
                for columna in columnas_insertables:
                    if columna == 'fecha_creacion':
                        valores.append(item.fecha_creacion.isoformat(sep=' '))
                    elif columna == 'es_automatico':
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


def limpiar_backups_en_progreso_viejos(minutos=60):
    """Elimina registros de backup en progreso que ya quedaron obsoletos."""
    from .models import BackupRecord

    try:
        minutos = int(minutos)
    except (TypeError, ValueError):
        minutos = 60

    minutos = max(1, minutos)
    cutoff = timezone.now() - timedelta(minutes=minutos)

    candidatos = BackupRecord.objects.filter(
        estado='en_progreso',
        fecha_creacion__lte=cutoff,
    ).order_by('fecha_creacion')

    eliminados = []
    for backup in candidatos:
        if backup.archivo and os.path.exists(backup.archivo):
            try:
                os.remove(backup.archivo)
            except OSError:
                pass
        eliminados.append(backup.nombre)
        backup.delete()

    return {
        'eliminados': len(eliminados),
        'nombres': eliminados,
        'minutos': minutos,
    }


def get_table_info():
    """Obtiene información detallada de todas las tablas."""
    tables = get_all_tables()
    info = []
    with connection.cursor() as cursor:
        for table in tables:
            try:
                cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
                count = cursor.fetchone()[0]
            except Exception:
                count = 0
            info.append({
                'nombre': table,
                'registros': count,
            })
    return info


def _normalizar_member_zip(nombre):
    """Normaliza una ruta interna del ZIP y valida que sea segura."""
    if not nombre:
        return None
    if nombre.endswith('/'):
        return None

    normalizado = os.path.normpath(nombre).replace('\\', '/')
    if os.path.isabs(nombre) or normalizado.startswith('../') or '/..' in normalizado:
        raise ValueError("El ZIP contiene rutas no permitidas.")
    return normalizado


def _media_relative_path(nombre_normalizado):
    """Devuelve la ruta relativa dentro de media/ o None si no corresponde."""
    if not nombre_normalizado:
        return None

    partes = nombre_normalizado.split('/')
    if 'media' not in partes:
        return None

    idx = partes.index('media')
    if idx == len(partes) - 1:
        return None

    return '/'.join(partes[idx + 1:])


def get_database_stats():
    """Obtiene estadísticas de la base de datos."""
    db_path = str(get_database_path())
    db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
    tables = get_table_info()
    total_registros = sum(t['registros'] for t in tables)

    # Tamaño de media
    media_root = getattr(settings, 'MEDIA_ROOT', '')
    media_size = 0
    media_files = 0
    if media_root and os.path.exists(str(media_root)):
        for dirpath, dirnames, filenames in os.walk(str(media_root)):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                media_size += os.path.getsize(fp)
                media_files += 1

    return {
        'db_size': db_size,
        'db_size_legible': _format_size(db_size),
        'total_tablas': len(tables),
        'total_registros': total_registros,
        'tablas': tables,
        'media_size': media_size,
        'media_size_legible': _format_size(media_size),
        'media_files': media_files,
    }


def validar_zip_backup_importado(uploaded_file):
    """Valida que el archivo subido sea un ZIP de backup compatible."""
    if not uploaded_file:
        raise ValueError("Debes seleccionar un archivo ZIP.")

    nombre_original = getattr(uploaded_file, 'name', '') or ''
    extension = os.path.splitext(nombre_original)[1].lower()
    if extension != '.zip':
        raise ValueError("Solo se permiten archivos .zip.")

    if getattr(uploaded_file, 'size', 0) <= 0:
        raise ValueError("El archivo ZIP está vacío.")

    backup_dir = get_backup_dir()
    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip', dir=backup_dir) as temp_file:
        for chunk in uploaded_file.chunks():
            temp_file.write(chunk)
        temp_path = temp_file.name

    try:
        if not zipfile.is_zipfile(temp_path):
            raise ValueError("El archivo no es un ZIP válido.")

        with zipfile.ZipFile(temp_path, 'r') as zf:
            nombres = zf.namelist()
            if not nombres:
                raise ValueError("El ZIP está vacío.")

            nombres_seguro = []
            db_members = []
            media_members = []

            for nombre in nombres:
                normalizado = _normalizar_member_zip(nombre)
                if not normalizado:
                    continue

                nombres_seguro.append(normalizado)
                if os.path.basename(normalizado).lower() == 'db.sqlite3':
                    db_members.append(normalizado)
                if _media_relative_path(normalizado) is not None:
                    media_members.append(normalizado)

            if 'backup_meta.json' not in nombres_seguro:
                raise ValueError("El ZIP debe incluir el archivo backup_meta.json.")

            try:
                meta = json.loads(zf.read('backup_meta.json').decode('utf-8'))
            except Exception as exc:
                raise ValueError("No se pudo leer backup_meta.json.") from exc

            tipo_meta = str(meta.get('tipo', '')).strip().lower()
            if tipo_meta not in {'completo', 'base_datos', 'media'}:
                raise ValueError("El backup no indica un tipo válido.")

            if tipo_meta in {'completo', 'base_datos'} and not db_members:
                raise ValueError("El ZIP no contiene la base de datos db.sqlite3.")

            if tipo_meta == 'media' and not media_members:
                raise ValueError("El ZIP no contiene archivos de media.")

            tablas_meta = meta.get('tablas')
            if tablas_meta is not None and not isinstance(tablas_meta, (list, tuple, str)):
                raise ValueError("El metadato de tablas no es válido.")

        return {
            'temp_path': temp_path,
            'meta': meta,
            'tipo': tipo_meta,
            'nombre_original': nombre_original,
        }
    except Exception:
        try:
            os.remove(temp_path)
        except OSError:
            pass
        raise


def importar_backup_desde_archivo(uploaded_file, usuario=None, notas=''):
    """Importa un archivo ZIP de backup y lo registra en el sistema."""
    from .models import BackupRecord

    validacion = validar_zip_backup_importado(uploaded_file)
    temp_path = validacion['temp_path']
    meta = validacion['meta']
    tipo = validacion['tipo']
    nombre_original = validacion['nombre_original']

    backup_dir = get_backup_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    nombre_base = str(meta.get('nombre') or os.path.splitext(os.path.basename(nombre_original))[0] or 'backup_importado').strip()
    nombre_base = re.sub(r'[^A-Za-z0-9_\-\.\s]+', '_', nombre_base).strip()
    if not nombre_base:
        nombre_base = f'backup_importado_{timestamp}'

    archivo_final = os.path.join(backup_dir, f'{nombre_base}.zip')
    if os.path.exists(archivo_final):
        archivo_final = os.path.join(backup_dir, f'{nombre_base}_{timestamp}.zip')

    try:
        shutil.copy2(temp_path, archivo_final)

        tablas_meta = meta.get('tablas')
        if isinstance(tablas_meta, (list, tuple)):
            tablas_incluidas = ', '.join(str(t) for t in tablas_meta)
        else:
            tablas_incluidas = str(tablas_meta or '')

        record = BackupRecord.objects.create(
            nombre=nombre_base,
            tipo=tipo,
            estado='exitoso',
            archivo=archivo_final,
            tamano=os.path.getsize(archivo_final),
            usuario=usuario,
            notas=notas.strip() or f'Importado desde {nombre_original}',
            tablas_incluidas=tablas_incluidas,
            duracion_segundos=0,
        )

        return record
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


def _format_size(size_bytes):
    """Formatea tamaño de bytes a formato legible."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def crear_backup_base_datos(nombre=None, usuario=None, notas=''):
    """Crea un backup de la base de datos SQLite."""
    from .models import BackupRecord

    start_time = time.time()
    backup_dir = get_backup_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Validar backup_dir
    if not backup_dir or not os.path.exists(backup_dir):
        raise FileNotFoundError(f"Directorio de backups no accesible: {backup_dir}")

    if not nombre:
        nombre = f"backup_bd_{timestamp}"
    
    # Sanitizar nombre
    nombre = nombre.strip()
    if not nombre:
        nombre = f"backup_bd_{timestamp}"

    filename = f"{nombre}.zip"
    filepath = os.path.join(backup_dir, filename)

    # Validar que el archivo no exista ya
    if os.path.exists(filepath):
        filepath = os.path.join(backup_dir, f"{nombre}_{timestamp}.zip")

    record = BackupRecord.objects.create(
        nombre=nombre,
        tipo='base_datos',
        estado='en_progreso',
        usuario=usuario,
        notas=notas,
    )

    try:
        db_path = str(get_database_path())
        
        # Validar BD existe
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Base de datos no encontrada: {db_path}")

        # Crear copia temporal de la BD usando la API de backup de SQLite
        temp_db = os.path.join(backup_dir, f"temp_{timestamp}.sqlite3")
        source = sqlite3.connect(db_path)
        dest = sqlite3.connect(temp_db)
        source.backup(dest)
        source.close()
        dest.close()

        # Validar que la copia temporal se creó
        if not os.path.exists(temp_db):
            raise FileNotFoundError("No se pudo crear la copia temporal de la base de datos")
        _limpiar_historial_backup_sqlite(temp_db)

        # Comprimir
        with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(temp_db, 'db.sqlite3')

            # Agregar metadatos
            meta = {
                'nombre': nombre,
                'tipo': 'base_datos',
                'fecha': datetime.now().isoformat(),
                'tablas': get_all_tables(),
                'usuario': str(usuario) if usuario else 'Sistema',
                'notas': notas,
            }
            zf.writestr('backup_meta.json', json.dumps(meta, indent=2, ensure_ascii=False))

        # Limpiar temporal
        if os.path.exists(temp_db):
            os.remove(temp_db)

        # Validar que el ZIP se creó correctamente
        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            raise FileNotFoundError("El archivo de backup no se creó correctamente")

        duration = time.time() - start_time
        file_size = os.path.getsize(filepath)

        record.archivo = filepath
        record.tamano = file_size
        record.estado = 'exitoso'
        record.duracion_segundos = round(duration, 2)
        record.tablas_incluidas = ', '.join(get_all_tables())
        record.save()

        _limpiar_backups_antiguos()

        return record

    except Exception as e:
        record.estado = 'fallido'
        record.notas = f"{notas}\nError: {str(e)}" if notas else f"Error: {str(e)}"
        record.duracion_segundos = round(time.time() - start_time, 2)
        record.save()
        
        # Limpiar archivo corrupto si existe
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass
        
        raise


def crear_backup_completo(nombre=None, usuario=None, notas=''):
    """Crea un backup completo (BD + Media)."""
    from .models import BackupRecord

    start_time = time.time()
    backup_dir = get_backup_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Validar backup_dir
    if not backup_dir or not os.path.exists(backup_dir):
        raise FileNotFoundError(f"Directorio de backups no accesible: {backup_dir}")

    if not nombre:
        nombre = f"backup_completo_{timestamp}"
    
    nombre = nombre.strip()
    if not nombre:
        nombre = f"backup_completo_{timestamp}"

    filename = f"{nombre}.zip"
    filepath = os.path.join(backup_dir, filename)

    if os.path.exists(filepath):
        filepath = os.path.join(backup_dir, f"{nombre}_{timestamp}.zip")

    record = BackupRecord.objects.create(
        nombre=nombre,
        tipo='completo',
        estado='en_progreso',
        usuario=usuario,
        notas=notas,
    )

    try:
        db_path = str(get_database_path())

        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Base de datos no encontrada: {db_path}")

        # Backup de BD
        temp_db = os.path.join(backup_dir, f"temp_{timestamp}.sqlite3")
        source = sqlite3.connect(db_path)
        dest = sqlite3.connect(temp_db)
        source.backup(dest)
        source.close()
        dest.close()

        if not os.path.exists(temp_db):
            raise FileNotFoundError("No se pudo crear la copia temporal de la base de datos")
        _limpiar_historial_backup_sqlite(temp_db)

        with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
            # BD
            zf.write(temp_db, 'db.sqlite3')

            # Media
            media_root = str(getattr(settings, 'MEDIA_ROOT', ''))
            media_files_count = 0
            if media_root and os.path.exists(media_root):
                for dirpath, dirnames, filenames in os.walk(media_root):
                    for f in filenames:
                        file_path = os.path.join(dirpath, f)
                        arc_name = os.path.join(
                            'media',
                            os.path.relpath(file_path, media_root)
                        )
                        zf.write(file_path, arc_name)
                        media_files_count += 1

            # Metadatos
            meta = {
                'nombre': nombre,
                'tipo': 'completo',
                'fecha': datetime.now().isoformat(),
                'tablas': get_all_tables(),
                'usuario': str(usuario) if usuario else 'Sistema',
                'notas': notas,
                'incluye_media': True,
                'media_files_count': media_files_count,
            }
            zf.writestr('backup_meta.json', json.dumps(meta, indent=2, ensure_ascii=False))

        if os.path.exists(temp_db):
            os.remove(temp_db)

        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            raise FileNotFoundError("El archivo de backup no se creó correctamente")

        duration = time.time() - start_time
        file_size = os.path.getsize(filepath)

        record.archivo = filepath
        record.tamano = file_size
        record.estado = 'exitoso'
        record.duracion_segundos = round(duration, 2)
        record.tablas_incluidas = ', '.join(get_all_tables())
        record.save()

        _limpiar_backups_antiguos()

        return record

    except Exception as e:
        record.estado = 'fallido'
        record.notas = f"{notas}\nError: {str(e)}" if notas else f"Error: {str(e)}"
        record.duracion_segundos = round(time.time() - start_time, 2)
        record.save()
        
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass
        
        raise


def crear_backup_media(nombre=None, usuario=None, notas=''):
    """Crea un backup solo de archivos media."""
    from .models import BackupRecord

    start_time = time.time()
    backup_dir = get_backup_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Validar backup_dir
    if not backup_dir or not os.path.exists(backup_dir):
        raise FileNotFoundError(f"Directorio de backups no accesible: {backup_dir}")

    media_root = str(getattr(settings, 'MEDIA_ROOT', ''))
    if not media_root or not os.path.exists(media_root):
        raise FileNotFoundError(f"Directorio de media no encontrado: {media_root}")

    if not nombre:
        nombre = f"backup_media_{timestamp}"

    nombre = nombre.strip()
    if not nombre:
        nombre = f"backup_media_{timestamp}"

    filename = f"{nombre}.zip"
    filepath = os.path.join(backup_dir, filename)

    if os.path.exists(filepath):
        filepath = os.path.join(backup_dir, f"{nombre}_{timestamp}.zip")

    record = BackupRecord.objects.create(
        nombre=nombre,
        tipo='media',
        estado='en_progreso',
        usuario=usuario,
        notas=notas,
    )

    try:
        files_added = 0
        total_size = 0

        with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
            for dirpath, dirnames, filenames in os.walk(media_root):
                for f in filenames:
                    file_path = os.path.join(dirpath, f)
                    arc_name = os.path.join(
                        'media',
                        os.path.relpath(file_path, media_root)
                    )
                    if os.path.exists(file_path):
                        zf.write(file_path, arc_name)
                        files_added += 1
                        total_size += os.path.getsize(file_path)

            # Metadatos
            meta = {
                'nombre': nombre,
                'tipo': 'media',
                'fecha': datetime.now().isoformat(),
                'usuario': str(usuario) if usuario else 'Sistema',
                'notas': notas,
                'files_count': files_added,
                'total_size_files': total_size,
            }
            zf.writestr('backup_meta.json', json.dumps(meta, indent=2, ensure_ascii=False))

        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            raise FileNotFoundError("El archivo de backup no se creó correctamente")

        duration = time.time() - start_time
        file_size = os.path.getsize(filepath)

        record.archivo = filepath
        record.tamano = file_size
        record.estado = 'exitoso'
        record.duracion_segundos = round(duration, 2)
        record.tablas_incluidas = f"{files_added} archivos de media"
        record.save()

        _limpiar_backups_antiguos()

        return record

    except Exception as e:
        record.estado = 'fallido'
        record.notas = f"{notas}\nError: {str(e)}" if notas else f"Error: {str(e)}"
        record.duracion_segundos = round(time.time() - start_time, 2)
        record.save()
        
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass
        
        raise


def restaurar_backup(record):
    """Restaura un backup previamente creado."""
    if not record.archivo or not os.path.exists(record.archivo):
        raise FileNotFoundError("El archivo de backup no existe.")

    backup_dir = get_backup_dir()
    historial_prev = _snapshot_historial_backup_actual()

    with zipfile.ZipFile(record.archivo, 'r') as zf:
        names = zf.namelist()

        # Restaurar BD
        db_member = next(
            (
                _normalizar_member_zip(name)
                for name in names
                if _normalizar_member_zip(name) and os.path.basename(_normalizar_member_zip(name)).lower() == 'db.sqlite3'
            ),
            None,
        )
        if db_member:
            db_path = str(get_database_path())

            # Cerrar conexiones activas
            connection.close()

            # Extraer BD temporal
            temp_db = os.path.join(backup_dir, 'restore_temp.sqlite3')
            with zf.open(db_member) as src, open(temp_db, 'wb') as dst:
                dst.write(src.read())

            # Reemplazar BD actual
            shutil.copy2(temp_db, db_path)
            os.remove(temp_db)
            _fusionar_historial_backup(historial_prev, db_path)

        # Restaurar Media
        media_files = [
            _normalizar_member_zip(n) for n in names
            if _normalizar_member_zip(n) and _media_relative_path(_normalizar_member_zip(n)) is not None
        ]
        if media_files:
            media_root = str(getattr(settings, 'MEDIA_ROOT', ''))
            if media_root:
                for mf in media_files:
                    relative_media = _media_relative_path(mf)
                    if not relative_media:
                        continue
                    target = os.path.join(media_root, relative_media)
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with zf.open(mf) as src, open(target, 'wb') as dst:
                        dst.write(src.read())

    record.estado = 'restaurado'
    record.save()

    return True


def _limpiar_backups_antiguos(dias=90):
    """Mantiene la función por compatibilidad, pero no borra nada automáticamente."""
    return {
        'eliminados': 0,
        'nombres': [],
        'minutos': dias,
    }


def obtener_info_backup_zip(filepath):
    """Lee los metadatos de un archivo ZIP de backup."""
    try:
        with zipfile.ZipFile(filepath, 'r') as zf:
            nombres = zf.namelist()
            meta = None
            archivos = []
            db_member = None
            media_members = []

            for nombre in nombres:
                normalizado = _normalizar_member_zip(nombre)
                if not normalizado:
                    continue

                if os.path.basename(normalizado).lower() == 'backup_meta.json':
                    try:
                        meta = json.loads(zf.read(nombre).decode('utf-8'))
                    except Exception:
                        meta = None
                    continue

                archivos.append(normalizado)
                if os.path.basename(normalizado).lower() == 'db.sqlite3':
                    db_member = normalizado
                if _media_relative_path(normalizado) is not None:
                    media_members.append(normalizado)

            return {
                'meta': meta,
                'archivos': archivos,
                'db_archivo': db_member,
                'media_archivos': media_members,
                'total_archivos': len(archivos),
                'tiene_db': bool(db_member),
                'tiene_media': bool(media_members),
            }
    except Exception:
        pass
    return None
