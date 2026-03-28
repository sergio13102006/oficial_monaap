from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import ProductoWeb
from .forms import ProductoWebForm


# ─────────────────────── LISTA ───────────────────────
@login_required
def lista_productos_web(request):
    productos = ProductoWeb.objects.all()

    # ── Filtros ──
    q = request.GET.get('q', '').strip()
    visible_filter = request.GET.get('visible', '').strip()
    orden = request.GET.get('orden', '').strip()
    current_sort = request.GET.get('sort', '').strip()
    current_dir = request.GET.get('dir', 'asc').strip().lower()
    if current_dir not in {'asc', 'desc'}:
        current_dir = 'asc'

    if q:
        productos = productos.filter(nombre__icontains=q)

    if visible_filter == 'si':
        productos = productos.filter(visible=True)
    elif visible_filter == 'no':
        productos = productos.filter(visible=False)

    orden_map = {
        'nombre_asc': 'nombre',
        'nombre_desc': '-nombre',
        'precio_asc': 'precio',
        'precio_desc': '-precio',
        'fecha_asc': 'fecha_creacion',
        'fecha_desc': '-fecha_creacion',
    }

    sort_map = {
        'nombre': ('nombre',),
        'precio': ('precio', 'nombre'),
        'estado': ('visible', 'nombre'),
        'fecha': ('fecha_creacion', 'nombre'),
    }

    if current_sort in sort_map:
        order_fields = []
        for field in sort_map[current_sort]:
            order_fields.append(field if current_dir == 'asc' else f'-{field}')
        productos = productos.order_by(*order_fields)
    elif orden in orden_map:
        productos = productos.order_by(orden_map[orden])
    else:
        current_sort = ''

    form = ProductoWebForm()                       # formulario para el modal "Agregar"
    return render(request, 'productos_web/lista.html', {
        'productos': productos,
        'form': form,
        'q': q,
        'visible_filter': visible_filter,
        'orden': orden,
        'current_sort': current_sort,
        'current_dir': current_dir,
        'suppress_base_messages': True,
    })


# ─────────────────────── CREAR ───────────────────────
@login_required
def crear_producto_web(request):
    if request.method == 'POST':
        form = ProductoWebForm(request.POST, request.FILES)
        if form.is_valid():
            producto = form.save()
            messages.success(request, f'Producto "{producto.nombre}" creado exitosamente.')
            return redirect('productos_web:lista')
        else:
            messages.error(request, 'Corrige los errores del formulario.')
    else:
        form = ProductoWebForm()

    return render(request, 'productos_web/form.html', {
        'form': form,
        'titulo': 'Agregar Producto Web',
    })


# ─────────────────── DETALLE JSON (AJAX) ─────────────
@login_required
def detalle_producto_web_json(request, pk):
    """Devuelve los datos del producto como JSON para poblar el modal de edición."""
    producto = get_object_or_404(ProductoWeb, pk=pk)
    return JsonResponse({
        'id': str(producto.pk),
        'nombre': producto.nombre,
        'precio': str(producto.precio),
        'descripcion': producto.descripcion or '',
        'imagen_url': producto.imagen.url if producto.imagen else '',
        'visible': producto.visible,
    })


@login_required
def validar_nombre_producto_web(request):
    nombre = (request.GET.get('nombre') or '').strip()
    producto_id = (request.GET.get('producto_id') or '').strip()

    if not nombre:
        return JsonResponse({
            'valid': False,
            'message': 'El nombre del producto es obligatorio.',
        })

    qs = ProductoWeb.objects.filter(nombre__iexact=nombre)
    if producto_id:
        qs = qs.exclude(pk=producto_id)

    if qs.exists():
        return JsonResponse({
            'valid': False,
            'message': 'Ya existe un producto con este nombre.',
        })

    return JsonResponse({
        'valid': True,
        'message': '',
    })


# ─────────────────────── EDITAR ──────────────────────
@login_required
def editar_producto_web(request, pk):
    producto = get_object_or_404(ProductoWeb, pk=pk)

    if request.method == 'POST':
        form = ProductoWebForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, f'Producto "{producto.nombre}" actualizado.')
            return redirect('productos_web:lista')
        else:
            messages.error(request, 'Corrige los errores del formulario.')
            return redirect('productos_web:lista')
    else:
        form = ProductoWebForm(instance=producto)

    return render(request, 'productos_web/form.html', {
        'form': form,
        'titulo': 'Editar Producto Web',
        'producto': producto,
    })


# ─────────────────────── ELIMINAR ────────────────────
@login_required
def eliminar_producto_web(request, pk):
    producto = get_object_or_404(ProductoWeb, pk=pk)

    if request.method == 'POST':
        nombre = producto.nombre
        producto.delete()
        messages.success(request, f'Producto "{nombre}" eliminado del catálogo web.')
        return redirect('productos_web:lista')

    return render(request, 'productos_web/confirmar_eliminar.html', {
        'producto': producto,
    })


# ─────────────────── TOGGLE VISIBILIDAD (AJAX) ──────
@login_required
@require_POST
def toggle_visible(request, pk):
    """Cambia visible/oculto vía AJAX y devuelve JSON."""
    producto = get_object_or_404(ProductoWeb, pk=pk)
    producto.visible = not producto.visible
    producto.save(update_fields=['visible'])
    return JsonResponse({
        'ok': True,
        'visible': producto.visible,
    })
