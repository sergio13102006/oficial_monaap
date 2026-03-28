from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST, require_http_methods

from core.global_ordenamiento import apply_smart_sorting, sorting_context

from . import services
from .comprobante import build_comprobante_excel_response
from .forms import (
    CompraForm,
    DetalleCompraFormSet,
    DevolucionCompraForm,
    DetalleDevolucionCompraFormSet,
)
from .models import Compra, DevolucionCompra
# =========================
# Helpers
# =========================
def is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _detalles_compra_disponibles_para_devolucion(compra_id):
    detalles = []

    with transaction.atomic():
        compra = (
            Compra.objects
            .select_for_update()
            .select_related("proveedor")
            .get(pk=compra_id, anulada=False)
        )

        for d in (
            compra.detalles
            .select_for_update()
            .select_related("producto")
            .order_by("producto__nombre")
        ):
            cantidad_ya_devuelta = (
                d.detalles_devolucion
                .select_for_update()
                .filter(devolucion__anulada=False)
                .aggregate(total=Sum("cantidad"))["total"] or 0
            )

            disponible = max((d.cantidad or 0) - cantidad_ya_devuelta, 0)

            if disponible <= 0:
                continue

            detalles.append({
                "id": d.id,
                "texto": (
                    f"{d.producto.nombre} | "
                    f"Comprado: {d.cantidad} | "
                    f"Devuelto: {cantidad_ya_devuelta} | "
                    f"Disponible: {disponible} | "
                    f"Precio: ${d.precio_unitario}"
                ),
                "precio_unitario": int(d.precio_unitario or 0),
                "disponible": disponible,
            })

    return detalles

def permiso_requerido(permisos, mensaje="No tienes permisos para realizar esta acción."):
    permisos = tuple(permisos) if isinstance(permisos, (list, tuple, set)) else (permisos,)

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_superuser or request.user.has_perms(permisos):
                return view_func(request, *args, **kwargs)

            if is_ajax(request):
                return JsonResponse({"success": False, "message": mensaje}, status=403)

            raise PermissionDenied(mensaje)

        return _wrapped_view

    return decorator

# =========================
# Listado principal
# =========================
@ensure_csrf_cookie
@login_required
@require_http_methods(["GET"])
def lista_compras(request):
    tipo = request.GET.get("tipo", "compras").strip()
    estado = request.GET.get("estado", "activas").strip()
    fecha = request.GET.get("fecha", "").strip()
    fecha_desde = request.GET.get("fecha_desde", "").strip()
    fecha_hasta = request.GET.get("fecha_hasta", "").strip()
    busqueda = request.GET.get("q", "").strip()

    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        fecha_desde, fecha_hasta = fecha_hasta, fecha_desde

    context = {
        "tipo_actual": tipo,
        "estado_actual": estado,
        "fecha_actual": fecha,
        "fecha_desde_actual": fecha_desde,
        "fecha_hasta_actual": fecha_hasta,
        "q_actual": busqueda,
    }

    if tipo == "devoluciones":
        devoluciones_qs = (
            DevolucionCompra.objects
            .select_related("compra", "proveedor", "usuario")
            .prefetch_related("detalles__producto")
            .order_by("-id")
        )

        if estado == "anuladas":
            devoluciones_qs = devoluciones_qs.filter(anulada=True)
        elif estado == "todas":
            pass
        else:
            devoluciones_qs = devoluciones_qs.filter(anulada=False)
            estado = "activas"

        if estado == "anuladas":
            if fecha:
                devoluciones_qs = devoluciones_qs.filter(fecha_anulada=fecha)
            if fecha_desde:
                devoluciones_qs = devoluciones_qs.filter(fecha_anulada__gte=fecha_desde)
            if fecha_hasta:
                devoluciones_qs = devoluciones_qs.filter(fecha_anulada__lte=fecha_hasta)
        else:
            if fecha:
                devoluciones_qs = devoluciones_qs.filter(fecha=fecha)
            if fecha_desde:
                devoluciones_qs = devoluciones_qs.filter(fecha__gte=fecha_desde)
            if fecha_hasta:
                devoluciones_qs = devoluciones_qs.filter(fecha__lte=fecha_hasta)

        if busqueda:
            filtros = (
                Q(id__icontains=busqueda) |
                Q(compra__id__icontains=busqueda) |
                Q(proveedor__nombre_proveedor__icontains=busqueda) |
                Q(usuario__username__icontains=busqueda)
            )
            devoluciones_qs = devoluciones_qs.filter(filtros)

        devoluciones_qs, sort_key, direction = apply_smart_sorting(
            request,
            devoluciones_qs,
            default_sort="id",
            default_dir="desc",
            aliases={
                "id": "id",
                "proveedor": "proveedor__nombre_proveedor",
                "fecha": "fecha",
                "usuario": "usuario__username",
                "anulada": "anulada",
            },
        )

        total_devoluciones = devoluciones_qs.aggregate(total=Sum("total"))["total"] or 0

        context.update({
            "devoluciones": devoluciones_qs,
            "total_general": total_devoluciones,
            "titulo_modulo": "Gestión de Devoluciones",
            "label_total": "Total devoluciones registradas",
            "placeholder_busqueda": "ID devolución, ID compra, proveedor o usuario",
            **sorting_context(sort_key, direction),
        })

    else:
        tipo = "compras"

        compras_qs = (
            Compra.objects
            .select_related("proveedor", "usuario")
            .prefetch_related("detalles__producto")
            .annotate(
                devoluciones_activas_count=Count(
                    "devoluciones",
                    filter=Q(devoluciones__anulada=False),
                    distinct=True
                )
            )
            .order_by("-id")
        )

        if estado == "anuladas":
            compras_qs = compras_qs.filter(anulada=True)
        elif estado == "todas":
            pass
        else:
            compras_qs = compras_qs.filter(anulada=False)
            estado = "activas"

        if estado == "anuladas":
            if fecha:
                compras_qs = compras_qs.filter(fecha_anulada=fecha)
            if fecha_desde:
                compras_qs = compras_qs.filter(fecha_anulada__gte=fecha_desde)
            if fecha_hasta:
                compras_qs = compras_qs.filter(fecha_anulada__lte=fecha_hasta)
        else:
            if fecha:
                compras_qs = compras_qs.filter(fecha=fecha)
            if fecha_desde:
                compras_qs = compras_qs.filter(fecha__gte=fecha_desde)
            if fecha_hasta:
                compras_qs = compras_qs.filter(fecha__lte=fecha_hasta)

        if busqueda:
            filtros = (
                Q(id__icontains=busqueda) |
                Q(proveedor__id__icontains=busqueda) |
                Q(proveedor__nombre_proveedor__icontains=busqueda) |
                Q(usuario__username__icontains=busqueda) |
                Q(usuario__id__icontains=busqueda)
            )
            compras_qs = compras_qs.filter(filtros)

        compras_qs, sort_key, direction = apply_smart_sorting(
            request,
            compras_qs,
            default_sort="id",
            default_dir="desc",
            aliases={
                "id": "id",
                "proveedor": "proveedor__nombre_proveedor",
                "fecha": "fecha",
                "usuario": "usuario__username",
                "anulada": "anulada",
            },
        )

        total_compras = compras_qs.aggregate(total=Sum("precio_total"))["total"] or 0

        context.update({
            "compras": compras_qs,
            "total_general": total_compras,
            "titulo_modulo": "Gestión de Compras",
            "label_total": "Total compras registradas",
            "placeholder_busqueda": "ID compra, ID proveedor, proveedor o usuario",
            **sorting_context(sort_key, direction),
        })

    context["tipo_actual"] = tipo
    context["estado_actual"] = estado

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render(request, "compras/lista_resultados_global.html", context)

    return render(request, "compras/compra.html", context)

# =========================
# Detalle de compra
# =========================
@login_required
@permiso_requerido("compras.view_compra", "No tienes permisos para ver compras.")
@require_http_methods(["GET"])
def detalle_compra(request, compra_id):
    compra = get_object_or_404(
        Compra.objects.select_related("proveedor", "usuario")
        .prefetch_related("detalles__producto"),
        id=compra_id
    )

    detalles_calc = []
    total_calc = 0

    for d in compra.detalles.all():
        subtotal = float(d.cantidad) * float(d.precio_unitario)
        total_calc += subtotal
        detalles_calc.append({
            "producto": d.producto.nombre,
            "cantidad": d.cantidad,
            "precio_unitario": float(d.precio_unitario),
            "subtotal": subtotal,
        })

    html = render_to_string(
        "compras/detalle_compra.html",
        {"c": compra, "detalles_calc": detalles_calc, "total_calc": total_calc},
        request=request
    )
    return JsonResponse({"success": True, "html": html})

@login_required
@permiso_requerido("compras.add_compra", "No tienes permisos para registrar compras.")
@require_http_methods(["GET", "POST"])
def crear_compra(request):
    if request.method == "POST":
        form = CompraForm(request.POST)
        formset = DetalleCompraFormSet(request.POST, prefix="detalles")

        if form.is_valid() and formset.is_valid():
            try:
                services.registrar_compra(
                    form=form,
                    formset=formset,
                    usuario=request.user,
                )
            except services.CompraServiceError as exc:
                form.add_error(None, str(exc))
            else:
                # messages.success(request, "Compra registrada correctamente.")
                if is_ajax(request):
                    return JsonResponse({"success": True})
                return redirect("compras:lista_compras")

        context = {
            "form": form,
            "formset": formset,
            "action_url": reverse("compras:crear_compra"),
            "compra": None,
            "modo": "crear",
        }

        if is_ajax(request):
            html = render_to_string(
                "compras/formulario_crear_compra.html",
                context,
                request=request
            )
            return JsonResponse({"success": False, "html": html}, status=400)

        return render(request, "compras/crear_compra.html", context)

    form = CompraForm()
    formset = DetalleCompraFormSet(prefix="detalles")
    context = {
        "form": form,
        "formset": formset,
        "action_url": reverse("compras:crear_compra"),
        "compra": None,
        "modo": "crear",
    }

    if is_ajax(request):
        html = render_to_string(
            "compras/formulario_crear_compra.html",
            context,
            request=request
        )
        return JsonResponse({"success": True, "html": html})

    return render(request, "compras/crear_compra.html", context)


@login_required
@permiso_requerido("compras.change_compra", "No tienes permisos para editar compras.")
@require_http_methods(["GET", "POST"])
def editar_compra(request, pk):
    compra = get_object_or_404(Compra, pk=pk)
    prefix = "detalles"

    try:
        services.validar_compra_editable(compra)
    except services.CompraServiceError as exc:
        if is_ajax(request):
            return JsonResponse(
                {"success": False, "message": str(exc)},
                status=400
            )

        return render(request, "compras/formulario_editar.html", {
            "compra": compra,
            "form": CompraForm(instance=compra),
            "formset": DetalleCompraFormSet(instance=compra, prefix=prefix),
            "modo": "editar",
            "action_url": reverse("compras:editar_compra", args=[compra.pk]),
            "error": str(exc),
        })

    if request.method == "POST":
        form = CompraForm(request.POST, instance=compra)
        formset = DetalleCompraFormSet(request.POST, instance=compra, prefix=prefix)

        if form.is_valid() and formset.is_valid():
            try:
                services.editar_compra(
                    compra=compra,
                    form=form,
                    formset=formset,
                    usuario=request.user,
                )
            except services.CompraServiceError as exc:
                form.add_error(None, str(exc))
            else:
                if is_ajax(request):
                    return JsonResponse({
                        "success": True,
                        "message": "Se editó correctamente"
                    })

                messages.success(request, "Compra editada correctamente.")
                return redirect("compras:lista_compras")

        html = render_to_string(
            "compras/formulario_editar.html",
            {
                "form": form,
                "formset": formset,
                "compra": compra,
                "modo": "editar",
                "action_url": reverse("compras:editar_compra", args=[compra.pk]),
            },
            request=request
        )

        if is_ajax(request):
            return JsonResponse({"success": False, "html": html}, status=400)

        return render(request, "compras/formulario_editar.html", {
            "form": form,
            "formset": formset,
            "compra": compra,
            "modo": "editar",
            "action_url": reverse("compras:editar_compra", args=[compra.pk]),
        })

    form = CompraForm(instance=compra)
    formset = DetalleCompraFormSet(instance=compra, prefix=prefix)

    context = {
        "form": form,
        "formset": formset,
        "compra": compra,
        "modo": "editar",
        "action_url": reverse("compras:editar_compra", args=[compra.pk]),
    }

    if is_ajax(request):
        html = render_to_string("compras/formulario_editar.html", context, request=request)
        return JsonResponse({"success": True, "html": html})

    return render(request, "compras/formulario_editar.html", context)

@login_required
@permiso_requerido("compras.change_compra", "No tienes permisos para anular compras.")
@require_POST
def anular_compra(request, pk):
    compra = get_object_or_404(
        Compra.objects.prefetch_related("detalles__producto"),
        pk=pk
    )

    try:
        services.anular_compra(
            compra=compra,
            usuario=request.user,
        )
    except services.CompraServiceError as exc:
        if str(exc) == "La compra ya estaba anulada.":
            return JsonResponse({
                "status": "already",
                "message": str(exc)
            })

        return JsonResponse({
            "success": False,
            "message": str(exc)
        }, status=400)

    return JsonResponse({
        "success": True,
        "message": "Compra anulada y stock revertido."
    })

# =========================
# Comprobantes de compra
# =========================
@login_required
@permiso_requerido("compras.view_compra", "No tienes permisos para ver comprobantes de compra.")
def comprobante_compra_preview(request, pk):
    compra = get_object_or_404(
        Compra.objects.select_related("proveedor", "usuario")
        .prefetch_related("detalles__producto"),
        pk=pk
    )

    html = render_to_string(
        "compras/comprobante_vista_previa.html",
        {"compra": compra},
        request=request
    )
    return JsonResponse({"success": True, "html": html})



@login_required
@permiso_requerido("compras.view_compra", "No tienes permisos para exportar comprobantes de compra.")
def comprobante_compra_excel(request, pk):
    compra = get_object_or_404(
        Compra.objects.select_related("proveedor", "usuario")
        .prefetch_related("detalles__producto"),
        pk=pk
    )
    return build_comprobante_excel_response(compra)

# =========================
# Devoluciones de compra
# =========================
@login_required
@permiso_requerido("compras.add_devolucioncompra", "No tienes permisos para registrar devoluciones.")
@require_http_methods(["GET", "POST"])
def crear_devolucion_compra(request):
    compra_ref = None

    if request.method == "POST":
        form = DevolucionCompraForm(request.POST)

        compra_id = request.POST.get("compra")
        if compra_id:
            compra_ref = Compra.objects.filter(pk=compra_id, anulada=False).first()

        formset = DetalleDevolucionCompraFormSet(
            request.POST,
            prefix="detalles",
            form_kwargs={"compra": compra_ref}
        )

        if form.is_valid() and formset.is_valid():
            try:
                services.registrar_devolucion_compra(
                    form=form,
                    formset=formset,
                    usuario=request.user,
                )
            except services.CompraServiceError as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(request, "Devolución registrada correctamente.")
                if is_ajax(request):
                    return JsonResponse({"success": True})
                return redirect("compras:lista_compras")

        context = {
            "form": form,
            "formset": formset,
            "action_url": reverse("compras:crear_devolucion_compra"),
            "modo": "crear",
        }

        if is_ajax(request):
            html = render_to_string(
                "compras/form_devolucion.html",
                context,
                request=request
            )
            return JsonResponse({"success": False, "html": html}, status=400)

        return render(request, "compras/crear_devolucion.html", context)

    form = DevolucionCompraForm()
    formset = DetalleDevolucionCompraFormSet(
        prefix="detalles",
        form_kwargs={"compra": compra_ref}
    )

    context = {
        "form": form,
        "formset": formset,
        "action_url": reverse("compras:crear_devolucion_compra"),
        "modo": "crear",
    }

    if is_ajax(request):
        html = render_to_string(
            "compras/form_devolucion.html",
            context,
            request=request
        )
        return JsonResponse({"success": True, "html": html})

    return render(request, "compras/crear_devolucion.html", context)

@login_required
@permiso_requerido("compras.add_devolucioncompra", "No tienes permisos para consultar detalles de devoluciones.")
@require_http_methods(["GET"])
def cargar_detalles_compra(request):
    compra_id = (request.GET.get("compra_id") or "").strip()

    if not compra_id or not compra_id.isdigit():
        return JsonResponse({"success": False, "detalles": [], "message": "Compra inválida."}, status=400)

    try:
        detalles = _detalles_compra_disponibles_para_devolucion(int(compra_id))
    except Compra.DoesNotExist:
        return JsonResponse(
            {"success": False, "detalles": [], "message": "Compra invalida o anulada."},
            status=404,
        )

    return JsonResponse({"success": True, "detalles": detalles})

@login_required
@permiso_requerido("compras.change_devolucioncompra", "No tienes permisos para anular devoluciones.")
@require_POST
def anular_devolucion_compra(request, pk):
    devolucion = get_object_or_404(
        DevolucionCompra.objects.prefetch_related("detalles__producto"),
        pk=pk
    )

    try:
        services.anular_devolucion_compra(
            devolucion=devolucion,
            usuario=request.user,
        )
    except services.CompraServiceError as exc:
        return JsonResponse({
            "success": False,
            "message": str(exc)
        })

    return JsonResponse({
        "success": True,
        "message": "Devolución anulada y stock restaurado."
    })

# =========================
# Comprobante de devolución
# =========================
@login_required
@permiso_requerido("compras.view_devolucioncompra", "No tienes permisos para ver devoluciones.")
@require_http_methods(["GET"])
def comprobante_devolucion_compra_preview(request, pk):
    devolucion = get_object_or_404(
        DevolucionCompra.objects
        .select_related("compra", "proveedor", "usuario")
        .prefetch_related("detalles__producto"),
        pk=pk
    )

    html = render_to_string(
        "compras/detalle_devolucion_compra.html",
        {
            "d": devolucion,
            "titulo_documento": "Comprobante de devolución de compra",
            "logo_src": static("compras/img/logo_monakeratina.png"),
            "watermark_src": static("compras/img/logo_monakeratina_watermark.png"),
        },
        request=request
    )
    return JsonResponse({"success": True, "html": html})

