import os
import json
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import FileResponse, JsonResponse, Http404
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator

from .models import BackupRecord, BackupConfig
from .services import (
    crear_backup_base_datos,
    crear_backup_completo,
    crear_backup_media,
    importar_backup_desde_archivo,
    restaurar_backup,
    get_database_stats,
    get_all_tables,
    obtener_info_backup_zip,
)


def es_administrador(user):
    return user.is_superuser or user.is_staff


# ======================== DASHBOARD DE BACKUP ========================

@login_required
@user_passes_test(es_administrador)
def backup_dashboard(request):
    """Vista principal del mÃ³dulo de backup."""
    query = request.GET.get('q', '').strip()
    current_sort = request.GET.get('sort', 'fecha').strip()
    current_dir = request.GET.get('dir', 'desc').strip().lower()
    if current_dir not in {'asc', 'desc'}:
        current_dir = 'desc'

    backups_qs = BackupRecord.objects.exclude(estado='en_progreso')
    if query:
        backups_qs = backups_qs.filter(
            Q(nombre__icontains=query)
            | Q(notas__icontains=query)
            | Q(tipo__icontains=query)
            | Q(estado__icontains=query)
            | Q(usuario__username__icontains=query)
        )
    estado = request.GET.get('estado', '').strip()
    tipo = request.GET.get('tipo', '').strip()
    fecha_desde_raw = request.GET.get('fecha_desde', '').strip()
    fecha_hasta_raw = request.GET.get('fecha_hasta', '').strip()

    if estado and estado in dict(BackupRecord.ESTADO_CHOICES):
        backups_qs = backups_qs.filter(estado=estado)
    if tipo and tipo in dict(BackupRecord.TIPO_CHOICES):
        backups_qs = backups_qs.filter(tipo=tipo)
    try:
        if fecha_desde_raw:
            backups_qs = backups_qs.filter(fecha_creacion__date__gte=date.fromisoformat(fecha_desde_raw))
    except ValueError:
        fecha_desde_raw = ''
    try:
        if fecha_hasta_raw:
            backups_qs = backups_qs.filter(fecha_creacion__date__lte=date.fromisoformat(fecha_hasta_raw))
    except ValueError:
        fecha_hasta_raw = ''

    sort_map = {
        'nombre': ('nombre',),
        'tipo': ('tipo', 'nombre'),
        'estado': ('estado', 'nombre'),
        'tamano': ('tamano', 'nombre'),
        'fecha': ('fecha_creacion',),
    }

    if current_sort in sort_map:
        order_fields = []
        for field in sort_map[current_sort]:
            order_fields.append(field if current_dir == 'asc' else f'-{field}')
        backups_qs = backups_qs.order_by(*order_fields)
    else:
        current_sort = 'fecha'
        current_dir = 'desc'
        backups_qs = backups_qs.order_by('-fecha_creacion')

    paginator = Paginator(backups_qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    backups = page_obj.object_list
    config = BackupConfig.get_config()
    stats = get_database_stats()

    # EstadÃ­sticas de backups
    total_backups = BackupRecord.objects.exclude(estado='en_progreso').count()
    exitosos = BackupRecord.objects.filter(estado='exitoso').count()
    fallidos = BackupRecord.objects.filter(estado='fallido').count()
    ultimo = BackupRecord.objects.filter(estado='exitoso').order_by('-fecha_creacion').first()
    historial_total = backups_qs.count()

    querystring = request.GET.copy()
    querystring.pop('page', None)

    context = {
        'backups': backups,
        'page_obj': page_obj,
        'config': config,
        'stats': stats,
        'total_backups': total_backups,
        'historial_total': historial_total,
        'exitosos': exitosos,
        'fallidos': fallidos,
        'ultimo_backup': ultimo,
        'query': query,
        'estado': estado,
        'tipo': tipo,
        'fecha_desde': fecha_desde_raw,
        'fecha_hasta': fecha_hasta_raw,
        'querystring': querystring.urlencode(),
        'tipo_choices': BackupRecord.TIPO_CHOICES,
        'estado_choices': BackupRecord.ESTADO_CHOICES,
        'current_sort': current_sort,
        'current_dir': current_dir,
    }
    return render(request, 'backup/dashboard.html', context)


# ======================== CREAR BACKUP ========================

@login_required
@user_passes_test(es_administrador)
@require_POST
def crear_backup(request):
    """Crea un nuevo backup completo."""
    nombre = request.POST.get('nombre', '').strip()
    notas = request.POST.get('notas', '').strip()

    if nombre:
        if len(nombre) < 3:
            messages.error(request, 'El nombre debe tener al menos 3 caracteres.')
            return redirect('backup:dashboard')
        if len(nombre) > 255:
            messages.error(request, 'El nombre no puede exceder 255 caracteres.')
            return redirect('backup:dashboard')

        import re
        if not re.fullmatch(r'[a-zA-Z0-9_\-áéíóúñ\s\.]+', nombre):
            messages.error(request, 'El nombre contiene caracteres no permitidos.')
            return redirect('backup:dashboard')

    if len(notas) > 500:
        messages.error(request, 'Las notas no pueden exceder 500 caracteres.')
        return redirect('backup:dashboard')

    try:
        record = crear_backup_completo(
            nombre=nombre or None,
            usuario=request.user,
            notas=notas,
        )

        config = BackupConfig.get_config()
        config.ultimo_backup = timezone.now()
        config.save()

        messages.success(
            request,
            f'Backup "{record.nombre}" creado correctamente como copia completa.'
        )
    except Exception as e:
        messages.error(request, f'No se pudo crear el backup: {str(e)}')

    return redirect('backup:dashboard')


@login_required
@user_passes_test(es_administrador)
@require_POST
def importar_backup_view(request):
    """Importa un archivo ZIP de backup compatible."""
    archivo = request.FILES.get('archivo_backup')
    notas = request.POST.get('notas', '').strip()
    restaurar_despues = request.POST.get('restaurar_despues') == 'on'

    if not archivo:
        messages.error(request, 'Debes seleccionar un archivo ZIP para importar.')
        return redirect('backup:dashboard')

    try:
        record = importar_backup_desde_archivo(
            archivo,
            usuario=request.user,
            notas=notas,
        )

        if restaurar_despues:
            try:
                restaurar_backup(record)
                if request.session.session_key:
                    # La restauración reemplaza la BD y puede borrar la fila de sesión.
                    request.session.cycle_key()
                messages.success(
                    request,
                    f'Backup "{record.nombre}" importado y restaurado correctamente. '
                    f'El archivo quedó registrado en el historial para futuras restauraciones.'
                )
            except Exception as e:
                messages.warning(
                    request,
                    f'Backup "{record.nombre}" importado correctamente, pero no se pudo restaurar: {str(e)}'
                )
        else:
            messages.success(
                request,
                f'Backup "{record.nombre}" importado correctamente. '
                f'Ya puedes restaurarlo desde el historial si lo necesitas.'
            )
    except ValueError as e:
        messages.error(request, str(e))
    except FileNotFoundError as e:
        messages.error(request, f'Error de archivo: {str(e)}')
    except Exception as e:
        messages.error(request, f'No se pudo importar el backup: {str(e)}')

    return redirect('backup:dashboard')


# ======================== DESCARGAR BACKUP ========================

@login_required
@user_passes_test(es_administrador)
def descargar_backup(request, pk):
    """Descarga un archivo de backup."""
    record = get_object_or_404(BackupRecord, pk=pk)

    if not record.archivo or not os.path.exists(record.archivo):
        messages.error(request, 'El archivo de backup no existe en el servidor.')
        return redirect('backup:dashboard')

    response = FileResponse(
        open(record.archivo, 'rb'),
        content_type='application/zip'
    )
    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(record.archivo)}"'
    return response


# ======================== RESTAURAR BACKUP ========================

@login_required
@user_passes_test(es_administrador)
@require_POST
def restaurar_backup_view(request, pk):
    """Restaura un backup previamente creado."""
    record = get_object_or_404(BackupRecord, pk=pk)

    try:
        restaurar_backup(record)
        if request.session.session_key:
            # La restauración reemplaza la BD y puede borrar la fila de sesión.
            # Generamos una nueva sesión en la BD restaurada para evitar SessionInterrupted.
            request.session.cycle_key()
        messages.success(
            request,
            f'Backup "{record.nombre}" restaurado exitosamente. '
            f'Por favor, reinicie el servidor para aplicar todos los cambios.'
        )
    except FileNotFoundError:
        messages.error(request, 'El archivo de backup no existe en el servidor.')
    except Exception as e:
        messages.error(request, f'Error al restaurar: {str(e)}')

    return redirect('backup:dashboard')


# ======================== ELIMINAR BACKUP ========================

@login_required
@user_passes_test(es_administrador)
@require_POST
def eliminar_backup(request, pk):
    """Elimina un registro de backup y su archivo."""
    record = get_object_or_404(BackupRecord, pk=pk)

    if record.archivo and os.path.exists(record.archivo):
        try:
            os.remove(record.archivo)
        except OSError:
            pass

    nombre = record.nombre
    record.delete()
    messages.success(request, f'Backup "{nombre}" eliminado correctamente.')

    return redirect('backup:dashboard')


# ======================== DETALLE BACKUP ========================

@login_required
@user_passes_test(es_administrador)
def detalle_backup(request, pk):
    """Muestra los detalles de un backup específico."""
    record = get_object_or_404(BackupRecord, pk=pk)

    meta = None
    if record.archivo and os.path.exists(record.archivo):
        meta = obtener_info_backup_zip(record.archivo)

    context = {
        'backup': record,
        'meta': meta,
    }
    if request.GET.get('modal') == '1' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'backup/detalle_modal_content.html', context)
    return render(request, 'backup/detalle.html', context)


# ======================== CONFIGURACIÓN ========================

@login_required
@user_passes_test(es_administrador)
def configuracion_backup(request):
    """Vista de configuración del módulo de backup."""
    config = BackupConfig.get_config()

    if request.method == 'POST':
        try:
            config.backup_automatico = request.POST.get('backup_automatico') == 'on'
            config.frecuencia_horas = int(request.POST.get('frecuencia_horas', 24))
            config.max_backups = int(request.POST.get('max_backups', 10))
            config.incluir_media = request.POST.get('incluir_media') == 'on'
            config.ruta_backups = request.POST.get('ruta_backups', '').strip()
            config.save()
            messages.success(request, 'Configuración guardada correctamente.')
            return redirect('backup:configuracion')
        except (TypeError, ValueError):
            messages.error(request, 'Revisa los valores numéricos de la configuración.')

    context = {
        'config': config,
    }
    return render(request, 'backup/configuracion.html', context)


# ======================== INFO BD (AJAX) ========================

@login_required
@user_passes_test(es_administrador)
def info_base_datos(request):
    """Devuelve información de la base de datos en formato JSON."""
    stats = get_database_stats()
    return JsonResponse(stats)


