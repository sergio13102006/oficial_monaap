import re

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from .forms import ServicioWebForm
from .models import ServicioWeb


_TEXTO_SEGURO_RE = re.compile(r'^[A-Za-z0-9ÁÉÍÓÚáéíóúÑñ\s]+$')


@login_required
def crear_servicio_web(request):
    is_modal = request.GET.get('modal') == '1' or request.POST.get('modal') == '1'
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST':
        form = ServicioWebForm(request.POST, request.FILES)

        if form.is_valid():
            servicio_web = form.save()

            if is_modal or is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': f'Servicio Web "{servicio_web.nombre}" creado exitosamente.'
                })

            messages.success(request, f'Servicio Web "{servicio_web.nombre}" creado exitosamente.')
            return redirect('servicios_web:lista_servicios_web')

        if is_modal or is_ajax:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)
    else:
        form = ServicioWebForm()

    template_name = 'servicios_web/_servicio_web_form.html' if is_modal else 'servicios_web/crear_servicio.html'

    context = {
        'form': form,
        'is_modal': is_modal,
        'servicio_web': None,
    }
    return render(request, template_name, context)


@login_required
def editar_servicio_web(request, pk):
    servicio_web = get_object_or_404(ServicioWeb, pk=pk)
    is_modal = request.GET.get('modal') == '1' or request.POST.get('modal') == '1'
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST':
        form = ServicioWebForm(request.POST, request.FILES, instance=servicio_web)

        if form.is_valid():
            servicio_web = form.save()

            if is_modal or is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': f'Servicio Web "{servicio_web.nombre}" actualizado exitosamente.'
                })

            messages.success(request, f'Servicio Web "{servicio_web.nombre}" actualizado exitosamente.')
            return redirect('servicios_web:lista_servicios_web')

        if is_modal or is_ajax:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)
    else:
        form = ServicioWebForm(instance=servicio_web)

    template_name = 'servicios_web/_servicio_web_form.html' if is_modal else 'servicios_web/editar_servicio.html'

    context = {
        'form': form,
        'servicio_web': servicio_web,
        'is_modal': is_modal,
    }
    return render(request, template_name, context)


@login_required
def lista_servicios_web(request):
    servicios_web = ServicioWeb.objects.all()

    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '').strip()

    if q:
        servicios_web = servicios_web.filter(
            Q(nombre__icontains=q) |
            Q(descripcion__icontains=q)
        )

    if estado.lower() in ('activo', 'inactivo'):
        servicios_web = servicios_web.filter(activo=(estado.lower() == 'activo'))

    context = {
        'servicios_web': servicios_web,
        'titulo': 'Lista de Servicios Web',
        'q': q,
        'estado': estado,
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'servicios_web/lista_servicios_web_global.html', context)

    return render(request, 'servicios_web/lista_servicios_web.html', context)


def servicios_web_publicos(request):
    servicios = ServicioWeb.objects.filter(activo=True).order_by('nombre')
    return render(request, 'servicios_web/publicos.html', {
        'servicios': servicios
    })


@login_required
@require_POST
def cambiar_estado_servicio_web(request, pk):
    servicio = get_object_or_404(ServicioWeb, pk=pk)

    servicio.activo = not servicio.activo
    servicio.save()

    return JsonResponse({
        "success": True,
        "activo": servicio.activo
    })


@login_required
def eliminar_servicio_web(request, pk):
    servicio_web = get_object_or_404(ServicioWeb, pk=pk)

    if request.method == 'POST':
        nombre = servicio_web.nombre
        servicio_web.delete()
        messages.success(request, f'Servicio Web "{nombre}" eliminado exitosamente.')
        return redirect('servicios_web:lista_servicios_web')

    return render(request, 'servicios_web/eliminar_servicio.html', {
        'servicio_web': servicio_web,
    })


@login_required
def validar_nombre_servicio_web(request):
    nombre = (request.GET.get('nombre') or '').strip()
    servicio_id = request.GET.get('servicio_id')

    if not nombre:
        return JsonResponse({
            'valido': False,
            'mensaje': 'El nombre es obligatorio.'
        })

    if len(nombre) < 3:
        return JsonResponse({
            'valido': False,
            'mensaje': 'Debe tener al menos 3 caracteres.'
        })

    if not _TEXTO_SEGURO_RE.match(nombre):
        return JsonResponse({
            'valido': False,
            'mensaje': 'Solo se permiten letras, números y espacios.'
        })

    qs = ServicioWeb.objects.filter(nombre__iexact=nombre)

    if servicio_id:
        qs = qs.exclude(pk=servicio_id)

    if qs.exists():
        return JsonResponse({
            'valido': False,
            'mensaje': 'Ya existe un servicio web con este nombre.'
        })

    return JsonResponse({
        'valido': True,
        'mensaje': ''
    })
