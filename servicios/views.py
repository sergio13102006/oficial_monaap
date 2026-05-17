from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import Servicio
from .forms import ServicioForm
from gestion_alisados.models import GestionAlisado
from gestion_alisados.forms import GestionAlisadoForm
from servicios_web.models import ServicioWeb
from django.http import JsonResponse
def es_staff(user):
    return user.is_staff
@login_required
@ensure_csrf_cookie
def lista_servicios(request):
    servicios = Servicio.objects.all()
    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '').strip()

    if q:
        servicios = servicios.filter(nombre__icontains=q)
    if estado == 'activo':
        servicios = servicios.filter(activo=True)
    elif estado == 'inactivo':
        servicios = servicios.filter(activo=False)

    context = {'servicios': servicios, 'q': q, 'estado': estado}

    # Si es petición AJAX, devuelve solo el parcial
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'servicios/lista_servicios_global.html', context)

    return render(request, 'servicios/lista_servicios.html', context)


@login_required
def validar_nombre_servicio(request):
    nombre = (request.GET.get('nombre') or '').strip()
    servicio_id = (request.GET.get('servicio_id') or '').strip()

    if not nombre:
        return JsonResponse({
            'valid': False,
            'message': 'El nombre del servicio es obligatorio.'
        })

    qs = Servicio.objects.filter(nombre__iexact=nombre)
    if servicio_id:
        qs = qs.exclude(pk=servicio_id)

    if qs.exists():
        return JsonResponse({
            'valid': False,
            'message': 'Ya existe un servicio con este nombre.'
        })

    return JsonResponse({
        'valid': True,
        'message': ''
    })


def _primer_error_formulario(form):
    for errores in form.errors.values():
        if errores:
            return errores[0]
    return 'Corrige los errores del formulario.'


def _validation_error_a_dict(error):
    if hasattr(error, 'message_dict') and error.message_dict:
        return error.message_dict

    mensajes = getattr(error, 'messages', None) or [str(error)]
    return {'__all__': mensajes}


def _primer_mensaje_validation_error(error, fallback='No se pudo guardar el servicio.'):
    mensajes = getattr(error, 'messages', None)
    if mensajes:
        return mensajes[0]

    if hasattr(error, 'message_dict') and error.message_dict:
        for valores in error.message_dict.values():
            if valores:
                return valores[0]

    return fallback

@login_required
def crear_servicio(request):
    is_modal = request.GET.get('modal') == '1'
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST':
        form = ServicioForm(request.POST, request.FILES)

        if form.is_valid():
            try:
                servicio = form.save(commit=False)
                servicio.activo = True
                servicio.save()
            except ValidationError as error:
                errores = _validation_error_a_dict(error)
                mensaje_error = _primer_mensaje_validation_error(error)
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'errors': errores,
                        'message': mensaje_error
                    }, status=400)

                form.add_error(None, mensaje_error)
                messages.error(request, mensaje_error)
                return render(request, 'servicios/form_servicio.html', {
                    'form': form,
                    'titulo': 'Crear Servicio'
                })

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': f'Servicio "{servicio.nombre}" guardado correctamente.'
                })

            messages.success(request, f'Servicio "{servicio.nombre}" guardado correctamente.')
            return redirect('servicios:lista_servicios')

        if is_ajax:
            return JsonResponse({
                'success': False,
                'errors': form.errors,
                'message': _primer_error_formulario(form)
            }, status=400)

        messages.error(request, 'Corrige los errores del formulario.')
        return render(request, 'servicios/form_servicio.html', {
            'form': form,
            'titulo': 'Crear Servicio'
        })

    form = ServicioForm()

    context = {
        'form': form,
        'titulo': 'Crear Servicio'
    }

    if is_modal:
        return render(request, 'servicios/form_servicio_modal_content.html', context)

    return render(request, 'servicios/form_servicio.html', context)


@login_required
def editar_servicio(request, pk):
    servicio = get_object_or_404(Servicio, pk=pk)
    is_modal = request.GET.get('modal') == '1'
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST':
        form = ServicioForm(request.POST, request.FILES, instance=servicio)

        if form.is_valid():
            try:
                servicio = form.save()
            except ValidationError as error:
                errores = _validation_error_a_dict(error)
                mensaje_error = _primer_mensaje_validation_error(error, 'No se pudo actualizar el servicio.')
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'errors': errores,
                        'message': mensaje_error
                    }, status=400)

                form.add_error(None, mensaje_error)
                messages.error(request, mensaje_error)
                return render(request, 'servicios/editar_servicio.html', {
                    'form': form,
                    'titulo': 'Editar Servicio',
                    'servicio': servicio
                })

            mensaje = f'Servicio "{servicio.nombre}" actualizado correctamente.'

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': mensaje
                })

            if not is_ajax:
                messages.success(request, mensaje)
            return redirect('servicios:lista_servicios')

        if is_ajax:
            return JsonResponse({
                'success': False,
                'errors': form.errors,
                'message': _primer_error_formulario(form)
            }, status=400)

    else:
        form = ServicioForm(instance=servicio)

    context = {
        'form': form,
        'titulo': 'Editar Servicio',
        'servicio': servicio
    }

    if is_modal:
        return render(request, 'servicios/form_editar_servicio_modal_content.html', context)

    return render(request, 'servicios/editar_servicio.html', context)

@login_required
def eliminar_servicio(request, pk):
    servicio = get_object_or_404(Servicio, pk=pk)
    is_modal = request.GET.get('modal') == '1'
    
    if request.method == 'POST':
        nombre = servicio.nombre
        try:
            servicio.delete()
        except ProtectedError:
            mensaje = f'No se puede eliminar "{nombre}" porque ya tiene ventas u otros registros asociados.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': mensaje
                }, status=400)
            messages.error(request, mensaje)
            return redirect('servicios:lista_servicios')
        
        # Si es una petición AJAX, devolver JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'Servicio "{nombre}" eliminado exitosamente.'
            })
        messages.success(request, f'Servicio "{nombre}" eliminado exitosamente.')
        return redirect('servicios:lista_servicios')
    
    # Si es modal, cargar solo el contenido del formulario
    if is_modal:
        context = {
            'servicio': servicio
        }
        return render(request, 'servicios/form_eliminar_servicio_modal_content.html', context)
    
    context = {
        'servicio': servicio
    }
    return render(request, 'servicios/eliminar_servicio.html', context)

@login_required
@require_POST
def toggle_activo_servicio(request, pk):
    if request.method == 'POST':
        servicio = get_object_or_404(Servicio, pk=pk)
        nuevo_estado = not servicio.activo
        Servicio.objects.filter(pk=servicio.pk).update(
            activo=nuevo_estado,
            fecha_modificacion=timezone.now(),
        )
        return JsonResponse({
            'success': True,
            'activo': nuevo_estado
        })
    return JsonResponse({'success': False}, status=400)

def servicios_publicos(request):
    """Vista pública para mostrar servicios en la página principal"""
    servicios = Servicio.objects.filter(activo=True)
    context = {
        'servicios': servicios
    }
    return render(request, 'servicios/servicios_publicos.html', context)

# Vistas para Gestion de datos
@login_required
def lista_gestion_alisados(request):
    """Lista todas las gestiones de datos registradas"""
    gestiones = GestionAlisado.objects.all()
    context = {
        'gestiones': gestiones
    }
    return render(request, 'servicios/lista_gestion_alisados.html', context)


@login_required
def crear_gestion_alisado(request):
    """Crea un nuevo registro de gestion de datos"""
    is_modal = request.GET.get('modal') == '1'
    cliente_id = request.GET.get('cliente_id')  # ✅ ahora existe

    if request.method == 'POST':
        form = GestionAlisadoForm(request.POST, request.FILES)
        if form.is_valid():
            gestion = form.save()

            # ✅ Respuesta AJAX
            if is_modal or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Gestión de datos registrada exitosamente.',
                    'id': gestion.pk,
                })

            messages.success(request, 'Gestión de datos registrada exitosamente.')
            return redirect('servicios:lista_gestion_alisados')
    else:
        if cliente_id:
            form = GestionAlisadoForm(initial={'cliente': cliente_id})
        else:
            form = GestionAlisadoForm()

   
    context = {
        'form': form,
        'titulo': 'Gestión de datos',
        'is_modal': is_modal
    }

    
    if is_modal:
        return render(request, 'servicios/form_gestion_alisado_modal_content.html', context)

    return render(request, 'servicios/form_gestion_alisado.html', context)


@login_required
@user_passes_test(es_staff)
def ver_gestion_alisado(request, pk):
    """Muestra los detalles de una gestion de datos"""
    gestion = get_object_or_404(GestionAlisado, pk=pk)
    context = {
        'gestion': gestion
    }
    return render(request, 'servicios/detalle_gestion_alisado.html', context)


@login_required
def editar_gestion_alisado(request, pk):
    """Edita una gestion de datos existente"""
    gestion = get_object_or_404(GestionAlisado, pk=pk)
    
    if request.method == 'POST':
        form = GestionAlisadoForm(request.POST, request.FILES, instance=gestion)
        if form.is_valid():
            gestion = form.save()
            messages.success(request, 'Gestion de datos actualizada exitosamente.')
            return redirect('servicios:ver_gestion_alisado', pk=gestion.pk)
    else:
        form = GestionAlisadoForm(instance=gestion)
    
    context = {
        'form': form,
        'titulo': 'Gestion de datos',
        'gestion': gestion
    }
    return render(request, 'servicios/form_gestion_alisado.html', context)


@login_required
def eliminar_gestion_alisado(request, pk):
    """Elimina una gestion de datos"""
    gestion = get_object_or_404(GestionAlisado, pk=pk)
    
    if request.method == 'POST':
        gestion.delete()
        messages.success(request, 'Gestion de datos eliminada exitosamente.')
        return redirect('servicios:lista_gestion_alisados')
    
    context = {
        'gestion': gestion
    }
    return render(request, 'servicios/eliminar_gestion_alisado.html', context)


# FUNCIÓN DESHABILITADA: El botón de crear cliente desde el modal fue eliminado
# Si necesitas crear clientes, dirígete a Clientes → Crear Cliente
# @login_required
# def crear_cliente_ajax(request):
#     """Crea un cliente mediante AJAX desde el formulario de gestion de datos"""
#     if request.method == 'POST':
#         datos = request.POST
#         print("Datos recibidos:", dict(datos))  # Debug
#         errores = validar_datos_cliente(datos)
#         
#         if errores:
#             print("Errores de validación:", errores)  # Debug
#             return JsonResponse({
#                 'success': False,
#                 'errores': errores
#             })
#         
#         try:
#             cliente = Cliente.objects.create(
#                 tipo_documento=datos['tipo_documento'],
#                 numero_documento=datos['numero_documento'],
#                 nombre=datos['nombre'],
#                 apellido=datos['apellido'],
#                 fecha_nacimiento=datos['fecha_nacimiento'],
#                 telefono=datos.get('telefono', ''),
#                 correo=datos.get('correo', ''),
#                 estado='activo'
#             )
#             print("Cliente creado exitosamente:", cliente.id)  # Debug
#             
#             return JsonResponse({
#                 'success': True,
#                 'cliente': {
#                     'id': cliente.id,
#                     'nombre_completo': f"{cliente.nombre} {cliente.apellido}",
#                     'numero_documento': cliente.numero_documento
#                 }
#             })
#         except Exception as e:
#             print("Error al crear cliente:", str(e))  # Debug
#             return JsonResponse({
#                 'success': False,
#                 'errores': {'general': [str(e)]}
#             })
#     
#     return JsonResponse({'success': False, 'error': 'Método no permitido'})

