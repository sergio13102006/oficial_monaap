import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import BackupConfigForm, BackupCreateForm, BackupImportForm
from .models import BackupConfig, BackupRecord
from .selectors import (
    get_backup_dashboard_summary,
    get_dashboard_page,
    get_database_stats,
)
from .services import (
    create_full_backup,
    import_backup,
    read_backup_metadata,
    restore_backup,
    update_backup_config,
)


def es_administrador(user):
    return user.is_superuser or user.is_staff


@login_required
@user_passes_test(es_administrador)
def backup_dashboard_view(request):
    page_data = get_dashboard_page(request.GET)
    summary = get_backup_dashboard_summary(page_data["queryset"])
    querystring = request.GET.copy()
    querystring.pop("page", None)
    context = {
        **summary,
        **page_data,
        "stats": get_database_stats(),
        "querystring": querystring.urlencode(),
        "tipo_choices": BackupRecord.TIPO_CHOICES,
        "estado_choices": BackupRecord.ESTADO_CHOICES,
        "create_form": BackupCreateForm(),
        "import_form": BackupImportForm(),
        "config_form": BackupConfigForm(instance=summary["config"]),
    }
    return render(request, "backup/dashboard.html", context)


@login_required
@user_passes_test(es_administrador)
@require_POST
def crear_backup_view(request):
    form = BackupCreateForm(request.POST)
    if not form.is_valid():
        messages.error(request, " ".join(form.errors.get("__all__", [])) or next(iter(form.errors.values()))[0])
        return redirect("backup:dashboard")

    try:
        record = create_full_backup(
            nombre=form.cleaned_data["nombre"] or None,
            usuario=request.user,
            notas=form.cleaned_data["notas"],
        )
        config = BackupConfig.get_config()
        config.ultimo_backup = record.fecha_creacion
        config.save()
        messages.success(
            request,
            f'Backup "{record.nombre}" creado correctamente como copia completa.',
        )
    except Exception as exc:
        messages.error(request, f"No se pudo crear el backup: {exc}")
    return redirect("backup:dashboard")


@login_required
@user_passes_test(es_administrador)
@require_POST
def importar_backup_view(request):
    form = BackupImportForm(request.POST, request.FILES)
    if not form.is_valid():
        error = next(iter(form.errors.values()))[0]
        messages.error(request, error)
        return redirect("backup:dashboard")

    try:
        record = import_backup(
            form.cleaned_data["archivo_backup"],
            usuario=request.user,
            notas=form.cleaned_data["notas"],
        )
        if form.cleaned_data["restaurar_despues"]:
            try:
                restore_backup(record, user=request.user, create_safety_backup=True)
                if request.session.session_key:
                    request.session.cycle_key()
                messages.success(
                    request,
                    f'Backup "{record.nombre}" importado y restaurado correctamente. '
                    "El archivo quedó registrado en el historial para futuras restauraciones.",
                )
            except Exception as exc:
                messages.warning(
                    request,
                    f'Backup "{record.nombre}" importado correctamente, pero no se pudo restaurar: {exc}',
                )
        else:
            messages.success(
                request,
                f'Backup "{record.nombre}" importado correctamente. Ya puedes restaurarlo desde el historial si lo necesitas.',
            )
    except Exception as exc:
        messages.error(request, f"No se pudo importar el backup: {exc}")
    return redirect("backup:dashboard")


@login_required
@user_passes_test(es_administrador)
def descargar_backup_view(request, pk):
    record = get_object_or_404(BackupRecord, pk=pk)
    if not record.archivo or not os.path.exists(record.archivo):
        messages.error(request, "El archivo de backup no existe en el servidor.")
        return redirect("backup:dashboard")
    response = FileResponse(open(record.archivo, "rb"), content_type="application/zip")
    response["Content-Disposition"] = (
        f'attachment; filename="{os.path.basename(record.archivo)}"'
    )
    return response


@login_required
@user_passes_test(es_administrador)
@require_POST
def restaurar_backup_view(request, pk):
    record = get_object_or_404(BackupRecord, pk=pk)
    try:
        restore_backup(record, user=request.user, create_safety_backup=True)
        if request.session.session_key:
            request.session.cycle_key()
        messages.success(
            request,
            f'Backup "{record.nombre}" restaurado exitosamente. Por favor, reinicie el servidor para aplicar todos los cambios.',
        )
    except FileNotFoundError:
        messages.error(request, "El archivo de backup no existe en el servidor.")
    except Exception as exc:
        mensaje = str(exc)
        if "requiere flujo de migracion/importacion" in mensaje:
            messages.error(
                request,
                "Este respaldo pertenece a otro motor y requiere migracion/importacion controlada; no se puede restaurar directamente desde este panel.",
            )
        else:
            messages.error(request, f"Error al restaurar: {mensaje}")
    return redirect("backup:dashboard")


@login_required
@user_passes_test(es_administrador)
@require_POST
def eliminar_backup_view(request, pk):
    record = get_object_or_404(BackupRecord, pk=pk)
    if record.archivo and os.path.exists(record.archivo):
        try:
            os.remove(record.archivo)
        except OSError:
            pass
    nombre = record.nombre
    record.delete()
    messages.success(request, f'Backup "{nombre}" eliminado correctamente.')
    return redirect("backup:dashboard")


@login_required
@user_passes_test(es_administrador)
def detalle_backup_view(request, pk):
    record = get_object_or_404(BackupRecord, pk=pk)
    meta = None
    if record.archivo and os.path.exists(record.archivo):
        meta = read_backup_metadata(record.archivo)
    context = {"backup": record, "meta": meta}
    if request.GET.get("modal") == "1" or request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "backup/detalle_modal_content.html", context)
    return render(request, "backup/detalle.html", context)


@login_required
@user_passes_test(es_administrador)
def configuracion_backup_view(request):
    config = BackupConfig.get_config()
    if request.method == "POST":
        form = BackupConfigForm(request.POST, instance=config)
        if form.is_valid():
            update_backup_config(form.cleaned_data)
            messages.success(request, "Configuración guardada correctamente.")
            return redirect("backup:configuracion")
        messages.error(request, "Revisa los valores numéricos de la configuración.")
    context = {"config": config, "form": BackupConfigForm(instance=config)}
    return render(request, "backup/configuracion.html", context)


@login_required
@user_passes_test(es_administrador)
def info_base_datos_view(request):
    return JsonResponse(get_database_stats())


# Backwards-compatible aliases
backup_dashboard = backup_dashboard_view
crear_backup = crear_backup_view
descargar_backup = descargar_backup_view
detalle_backup = detalle_backup_view
eliminar_backup = eliminar_backup_view
configuracion_backup = configuracion_backup_view
info_base_datos = info_base_datos_view
