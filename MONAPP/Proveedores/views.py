from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Count
from .models import Proveedor
from .forms import ProveedorcrearForm
from .forms import ProveedoreditarForm
from django.db.models.deletion import ProtectedError
from compras.models import DetalleCompra
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from django.urls import reverse

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models.deletion import ProtectedError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from core.global_ordenamiento import sorting_context,apply_smart_sorting

from .models import Proveedor
def is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


@login_required
def validar_nombre_proveedor(request):
    nombre = (request.GET.get("nombre") or "").strip()
    proveedor_id = (request.GET.get("proveedor_id") or "").strip()

    if not nombre:
        return JsonResponse({
            "valid": False,
            "message": "El nombre del proveedor es obligatorio.",
        })

    qs = Proveedor.objects.filter(nombre_proveedor__iexact=nombre)
    if proveedor_id:
        qs = qs.exclude(pk=proveedor_id)

    if qs.exists():
        return JsonResponse({
            "valid": False,
            "message": "Ya existe un proveedor con este nombre.",
        })

    return JsonResponse({
        "valid": True,
        "message": "",
    })

@login_required
def lista_proveedores(request):
    q = request.GET.get("q", "").strip()
    estado = request.GET.get("estado", "todos").strip()

    if estado not in ["activo", "inactivo", "todos"]:
        estado = "todos"

    proveedores = Proveedor.objects.all()

    if estado in ["activo", "inactivo"]:
        proveedores = proveedores.filter(estado=estado)

    if q:
        proveedores = proveedores.filter(
            Q(nombre_proveedor__icontains=q) |
            Q(nit__icontains=q) |
            Q(correo_proveedor__icontains=q)
        )

    proveedores, sort_key, direction = apply_smart_sorting(
        request,
        proveedores,
        default_sort="nombre_proveedor",
        default_dir="asc",
        aliases={
            "nit": "nit",
            "proveedor": "nombre_proveedor",
            "estado": "estado",
        }
    )

    context = {
        "proveedores": proveedores,
        "estado_actual": estado,
        "q": q,
        **sorting_context(sort_key, direction),
    }

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render(request, "proveedor/lista_proveedores_global.html", context)

    return render(
        request,
        "proveedor/lista_proveedor.html",
        context,
    )
@login_required
def crear_proveedor(request):
    form = ProveedorcrearForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        proveedor = form.save()
        messages.success(request, f'Proveedor "{proveedor.nombre_proveedor}" creado correctamente.')

        if is_ajax(request):
            return JsonResponse({
                "success": True,
                "redirect_url": reverse("proveedores:lista_proveedor")
            })

        return redirect("proveedores:lista_proveedor")

    context = {
        "form": form,
        "action_url": reverse("proveedores:crear_proveedor"),
        "submit_label": "Crear",
        "titulo": "Crear proveedor"
    }

    if is_ajax(request):
        html = render_to_string(
            "proveedor/formulario_global_proveedor.html",
            context,
            request=request
        )
        return JsonResponse({
            "success": False,
            "html": html,
            "title": context["titulo"],
            "redirect_url": reverse("proveedores:lista_proveedor")
        })

    return render(request, "proveedor/crear_proveedor.html", context)

@login_required
def editar_proveedor(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    form = ProveedorcrearForm(request.POST or None, instance=proveedor)

    if request.method == "POST":
        if form.is_valid():
            form.save()

            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": True})

            return redirect("proveedores:lista_proveedor")

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            html = render_to_string(
                "proveedor/formulario_global_proveedor.html",
                {
                    "form": form,
                    "action_url": reverse("proveedores:editar_proveedor", args=[pk]),
                    "titulo": "Editar proveedor",
                    "submit_label": "Actualizar"
                },
                request=request
            )
            return JsonResponse({
                "success": False,
                "html": html,
                "title": "Editar proveedor"
            })

    context = {
        "form": form,
        "action_url": reverse("proveedores:editar_proveedor", args=[pk]),
    }

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        html = render_to_string("proveedor/formulario_global_proveedor.html", context, request=request)
        return JsonResponse({
            "success": False,
            "html": html,

        })

    return render(request, "proveedor/editar_proveedor.html", context)



def is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"

@login_required
@require_POST
def eliminar_proveedor(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)

    try:
        proveedor.delete()

        if is_ajax(request):
            return JsonResponse({
                "success": True,
                "action": "deleted",
                "id": pk,
                "message": "Proveedor eliminado correctamente."
            })

        messages.success(request, "Proveedor eliminado correctamente.")
        return redirect("Proveedores:lista_proveedores")

    except ProtectedError:
        msg = (
            "Este proveedor está relacionado con compras u otros registros. "
            "No se puede eliminar, pero puedes desactivarlo."
        )

        if is_ajax(request):
            return JsonResponse({
                "success": False,
                "action": "confirm_deactivate",
                "id": proveedor.pk,
                "message": msg
            }, status=409)

        messages.warning(request, msg)
        return redirect("Proveedores:lista_proveedores")
    
@login_required
@require_POST
def reactivar_proveedor(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)

    if proveedor.estado != "activo":
        proveedor.estado = "activo"
        proveedor.save(update_fields=["estado"])

    msg = "Proveedor reactivado correctamente."

    if is_ajax(request):
        return JsonResponse({
            "success": True,
            "action": "reactivated",
            "id": proveedor.pk,
            "estado": proveedor.estado,
            "message": msg
        })

    messages.success(request, msg)
    return redirect("Proveedores:lista_proveedores")
@login_required
@require_POST
def desactivar_proveedor(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)

    if proveedor.estado != "inactivo":
        proveedor.estado = "inactivo"
        proveedor.save(update_fields=["estado"])

    msg = "Proveedor desactivado correctamente."

    if is_ajax(request):
        return JsonResponse({
            "success": True,
            "action": "deactivated",
            "id": proveedor.pk,
            "estado": proveedor.estado,
            "message": msg
        })

    messages.success(request, msg)
    return redirect("Proveedores:lista_proveedores")
