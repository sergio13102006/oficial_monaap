from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Count
from collections import Counter
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models.deletion import ProtectedError
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string

from .models import Producto
from .forms import ProductoForm
from compras.models import Compra, DetalleCompra
from core.global_ordenamiento import apply_smart_sorting,sorting_context
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

def is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"

@login_required
def lista_productos(request):
    qs = Producto.objects.all()

    linea = request.GET.get("linea", "").strip()
    estado = request.GET.get("estado", "activos").strip() or "activos"
    q = request.GET.get("q", "").strip()
    orden = request.GET.get("orden", "").strip()
    sort_param = request.GET.get("sort", "").strip()
    dir_param = request.GET.get("dir", "").strip()

    if linea:
        qs = qs.filter(linea__iexact=linea)

    if estado == "inactivos":
        qs = qs.filter(activo=False)
    elif estado == "todos":
        pass
    else:
        qs = qs.filter(activo=True)

    if q:
        filtros = (
            Q(nombre__icontains=q)
            | Q(codigo__icontains=q)
            | Q(marca__icontains=q)
            | Q(presentacion__icontains=q)
        )
        q_lower = q.lower()

        if q_lower in ["activo", "activa", "disponible", "si", "sí"]:
            filtros |= Q(activo=True)

        if q_lower in ["inactivo", "inactiva", "no"]:
            filtros |= Q(activo=False)

        qs = qs.filter(filtros)

    if sort_param or dir_param:
        qs, sort_key, direction = apply_smart_sorting(
            request,
            qs,
            default_sort="nombre",
            default_dir="asc",
            aliases={
                "codigo": "codigo",
                "nombre": "nombre",
                "linea": "linea",
                "marca": "marca",
            }
        )
    else:
        if orden == "codigo":
            qs = qs.order_by("codigo")
            sort_key, direction = "codigo", "asc"
        elif orden == "marca":
            qs = qs.order_by("marca")
            sort_key, direction = "marca", "asc"
        elif orden == "presentacion":
            qs = qs.order_by("presentacion")
            sort_key, direction = "presentacion", "asc"
        else:
            qs = qs.order_by("nombre")
            sort_key, direction = "nombre", "asc"

    total_productos = qs.count()

    productos_por_linea = (
        qs.exclude(linea__isnull=True)
        .exclude(linea="")
        .values("linea")
        .annotate(total=Count("codigo"))
        .order_by("linea")
    )

    context = {
        "productos": qs,
        "total_productos": total_productos,
        "productos_por_linea": productos_por_linea,
        "linea_seleccionada": linea,
        "estado_seleccionado": estado,
        "orden_actual": orden,
        "q": q,
        **sorting_context(sort_key, direction),
    }

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render(request, "productos/lista_productos_global.html", context)

    return render(request, "productos/lista_productos.html", context)

@login_required
def detalle_compra_json(request, id):

    compra = get_object_or_404(
        Compra.objects.prefetch_related("detalles__producto"),
        id=id
    )

    primer = compra.detalles.first()

    imagen = ""

    if primer:
        if primer.producto.imagen:
            imagen = primer.producto.imagen.url

    data = {
        "id": compra.id,
        "proveedor": str(compra.proveedor),
        "fecha": compra.fecha.strftime("%d de %B de %Y") if compra.fecha else "",
        "usuario": str(compra.usuario),
        "estado": "Activa" if compra.activo else "Anulada",
        "total": f"${compra.total:,.2f}",
        "imagen": imagen,
        "detalles": []
    }

    for d in compra.detalles.all():

        img = ""

        if d.producto.imagen:
            img = d.producto.imagen.url

        data["detalles"].append({
            "nombre": d.producto.nombre,
            "cantidad": d.cantidad,
            "precio_unitario": f"${d.precio_unitario:,.2f}",
            "subtotal": f"${d.subtotal:,.2f}",
            "imagen": img,
        })

    return JsonResponse(data)
@login_required
def crear_producto(request):
    form = ProductoForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        producto = form.save()
        messages.success(request, f'Producto "{producto.nombre}" creado correctamente.')

        if is_ajax(request):
            return JsonResponse({"success": True})

        return redirect("productos:lista_productos")

    context = {
        "form": form,
        "action_url": reverse("productos:crear_producto"),
        "submit_label": "Crear",
        "title": "Crear producto",
    }

    if is_ajax(request):
        html = render_to_string("productos/formulario_producto.html", context, request=request)
        return JsonResponse({"success": False, "html": html, "title": context["title"]})

    return render(request, "productos/crear_producto.html", context)

@login_required
def editar_producto(request, codigo):
    producto = get_object_or_404(Producto, codigo=codigo)
    form = ProductoForm(request.POST or None, request.FILES or None, instance=producto)
    if request.method == "POST" and form.is_valid():
        producto = form.save()
        messages.success(request, f'Producto "{producto.nombre}" actualizado.')

        if is_ajax(request):
            return JsonResponse({"success": True})

        return redirect("productos:lista_productos")

    context = {
        "form": form,
        "action_url": reverse("productos:editar_producto", args=[codigo]),
        "submit_label": "Guardar cambios",
        "title": f"Editar producto: {producto.nombre}",
        "producto": producto,
    }

    if is_ajax(request):
        html = render_to_string("productos/formulario_producto.html", context, request=request)
        return JsonResponse({"success": False, "html": html, "title": context["title"]})

    return render(request, "productos/editar_producto.html", context)


@login_required
def validar_nombre_producto(request):
    nombre = (request.GET.get("nombre") or "").strip()
    producto_id = (request.GET.get("producto_id") or "").strip()

    if not nombre:
        return JsonResponse({"valido": False, "mensaje": "El nombre es obligatorio."})

    if len(nombre) < 3:
        return JsonResponse({"valido": False, "mensaje": "Debe tener al menos 3 caracteres."})

    if not all(ch.isalnum() or ch.isspace() for ch in nombre):
        return JsonResponse({
            "valido": False,
            "mensaje": "El nombre solo puede contener letras, numeros y espacios.",
        })

    qs = Producto.objects.filter(nombre__iexact=nombre)

    if producto_id:
        try:
            qs = qs.exclude(pk=int(producto_id))
        except (TypeError, ValueError):
            pass

    if qs.exists():
        return JsonResponse({
            "valido": False,
            "mensaje": "Ya existe un producto con este nombre.",
        })

    return JsonResponse({"valido": True, "mensaje": ""})

@login_required
@require_POST
def eliminar_producto(request, codigo):
    producto = get_object_or_404(Producto, codigo=codigo)

    action = (request.POST.get("action") or "").lower().strip()
    force_deactivate = request.POST.get("force_deactivate") == "1"

    if action == "activate":
        producto.activo = True
        producto.save(update_fields=["activo"])
        return JsonResponse({"status": "activated"})

    if action == "deactivate" or force_deactivate:
        producto.activo = False
        producto.save(update_fields=["activo"])
        return JsonResponse({"status": "inactivated"})

    
    try:
        producto.delete()
        return JsonResponse({"status": "deleted"})
    except ProtectedError as e:
        labels = [obj._meta.verbose_name_plural for obj in e.protected_objects]
        counts = Counter(labels)
        detalles = [{"nombre": k, "cantidad": v} for k, v in counts.items()]

        return JsonResponse(
            {
                "status": "protected",
                "title": "No se puede eliminar",
                "message": "Este producto está relacionado con otros registros.",
                "detalles": detalles,
            },
            status=409
        )


@login_required
@require_POST
def toggle_activo_producto(request, codigo):
    producto = get_object_or_404(Producto, codigo=codigo)
    producto.activo = not producto.activo
    producto.save(update_fields=["activo"])

    return JsonResponse({
        "success": True,
        "activo": producto.activo,
    })
